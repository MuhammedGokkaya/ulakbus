# -*-  coding: utf-8 -*-

from zengine.forms import fields
from zengine import forms
from zengine.views.crud import CrudView, form_modifier
from ulakbus.models.personel import Personel, Atama, Izin
from ulakbus.models.auth import User
from ulakbus.models.hitap import HizmetKayitlari, HizmetBirlestirme
from ulakbus.models.form import Form, FormData
from datetime import timedelta, date, datetime

import json


class IzinIslemleri(CrudView):
    class Meta:
        # CrudViev icin kullanilacak temel Model
        model = 'Izin'

        # ozel bir eylem listesi hazirlayacagiz. bu sebeple listeyi bosaltiyoruz.
        # kayit tipine bagli olarak ekleyecegimiz eylemleri .append() ile ekleyecegiz
        # object_actions = [
        #     # {'fields': [0, ], 'cmd': 'show', 'mode': 'normal', 'show_as': 'link'},
        # ]

    def goster(self):
        yil = date.today().year
        self.list()
        personel = Personel.objects.get(self.input['id'])
        izin_gun = self.hizmet_izin_yil_hesapla(personel)
        kalan_izin = self.kalan_izin_hesapla()
        bu_yil_kalan_izin = getattr(kalan_izin['yillik'], str(yil), 0)
        gecen_yil_kalan_izin = getattr(kalan_izin['yillik'], str(yil - 1), 0)
        kalan_mazeret_izin = getattr(kalan_izin['mazeret'], str(yil), 0)

        # Personelin izin gün sayısı 365 günden azsa eklemeyi kaldır.
        # Personel pasifse eklemeyi kaldır.
        yil = date.today().year
        izin_hakki_yok_sartlari = [
            izin_gun < 365,
            self.personel_aktif,
            bu_yil_kalan_izin <= 0 and gecen_yil_kalan_izin <= 0 and kalan_mazeret_izin <= 0
        ]
        if any(izin_hakki_yok_sartlari):
            self.ListForm.add = None

        # TODO: Personel bilgileri tabloda gösterilecek
        self.output['object'] = {
            "type": "table",
            "fields": [
                {
                    "name": personel.ad,
                    "surname": personel.soyad
                },
                {
                    "gun": izin_gun,
                    "durum": "Aktif" if self.personel_aktif else "Pasif"
                }, {
                    "izinler": kalan_izin,
                    "hizmet_sure": izin_gun
                }
            ]
        }

    def emekli_sandigi_hesapla(self, personel):
        personel_hizmetler = HizmetKayitlari.objects.filter(tckn=personel.tckn)

        baslangic_liste = set()
        bitis_liste = set()

        for hizmet in personel_hizmetler:
            baslangic_liste.add(hizmet.baslama_tarihi)
            bitis_liste.add(hizmet.bitis_tarihi)

        # clean sets any of blank dates
        blank_dates = [date(1900, 1, 1), '']
        for d in blank_dates:
            if d in baslangic_liste:
                baslangic_liste.remove(d)
            if d in bitis_liste:
                bitis_liste.remove(d)

        # sort dates
        baslangic_liste = sorted(baslangic_liste)
        bitis_liste = sorted(bitis_liste)

        if len(baslangic_liste) > 0:
            self.ilk_izin_hakedis = baslangic_liste[0] + timedelta(365)
        else:
            self.ilk_izin_hakedis = date.today()

        toplam_sure = timedelta(0)
        son_baslama = None

        for baslangic in baslangic_liste:
            if son_baslama is None:
                son_baslama = baslangic
            elif len(bitis_liste) > 0 and baslangic >= bitis_liste[0]:
                toplam_sure += bitis_liste[0] - son_baslama
                son_baslama = baslangic
                bitis_liste.remove(bitis_liste[0])

        if son_baslama is None:
            personel_aktif = False
        elif len(bitis_liste) > 0:
            personel_aktif = False
            toplam_sure += bitis_liste[0] - son_baslama
        else:
            personel_aktif = True
            toplam_sure += date.today() - son_baslama

        # print str(int(toplam_sure.days / 360)) + " Yıl, " + str(int(toplam_sure.days % 360)) + " Gün"
        return toplam_sure.days, personel_aktif

    @staticmethod
    def sgk_hesapla(personel):
        personel_birlestirmeler = HizmetBirlestirme.objects.filter(tckn=personel.tckn)
        toplam_gun = 0

        for hizmet in personel_birlestirmeler:
            toplam_gun += hizmet.sure

        return toplam_gun

    def hizmet_izin_yil_hesapla(self, personel):
        emekli_sandigi_gun, aktif = self.emekli_sandigi_hesapla(personel)
        sgk_gun = self.sgk_hesapla(personel)
        self.personel_aktif = aktif
        return emekli_sandigi_gun + sgk_gun

    def kalan_izin_hesapla(self):
        query = self._apply_list_queries(self.object.objects.filter())
        yillik_izinler = dict()
        mazeret_izinler = dict()

        if self.ilk_izin_hakedis > date.today():
            return {'yillik': None, 'mazeret': None}

        for yil in range(self.ilk_izin_hakedis.year, date.today().year + 1):
            yillik_izinler[yil] = 20
            mazeret_izinler[yil] = 10

        for izin in query:
            if izin.tip == 1:
                yil = izin.baslangic.year - 1
                if yil in yillik_izinler.keys() and yillik_izinler[yil] > 0:
                    yillik_izinler[yil] -= (izin.bitis - izin.baslangic).days
                else:
                    yil += 1
                    yillik_izinler[yil] -= (izin.bitis - izin.baslangic).days
            elif izin.tip == 5:
                mazeret_izinler[yil] -= (izin.bitis - izin.baslangic).days

        return {'yillik': yillik_izinler, 'mazeret': mazeret_izinler}


class IzinBasvuru(CrudView):
    """Izin basvuru workflowuna ait methodları barındıran sınıftır.

    """

    class Meta:

        # CrudViev icin kullanilacak temel Model
        model = 'Izin'

    class IzinBasvuruForm(forms.JsonForm):
        from datetime import date
        izin_turleri = [(1, "Yıllık İzin"), (2, "Mazeret İzni"), (3, "Refakat İzni"),
                        (4, "Fazla Mesai İzni"), (5, "Ücretsiz İzin")]
        gecerli_yil = date.today().year
        yillar = [(gecerli_yil - 1, gecerli_yil - 1), (gecerli_yil, gecerli_yil)]

        izin_turu = fields.Integer("İzin Türü Seçiniz", choices=izin_turleri)
        izin_ait_yil = fields.Integer("Ait Olduğu Yıl", choices=yillar)
        izin_baslangic = fields.Date("İzin Başlangıç Tarihi")
        izin_bitis = fields.Date("İzin Bitiş Tarihi")
        izin_adres = fields.Text("İzindeki Adres")

        ileri = fields.Button("İleri")

    def izin_basvuru_formu_goster(self):
        """İzin başvurusu yapacak olan personele izin başvuru formunu gösteren method.

        """
        _form = self.IzinBasvuruForm(current=self.current, title="İzin Talep Formu")
        self.form_out(_form)

    def izin_basvuru_kaydet(self):
        """Personelin `IzinBasvuruForm` aracılığı ile yapmış olduğu başvuruyu kaydeden methoddur.
        Başvuruya ait veriler `Form` ve `FormData` modellerine kaydedilir. Form verileri, `FormData`
        modelinde `data` field'ıne kaydedilirken JSON tipine çevrilir.
        TODO: İzni onaylayacak olan personellere notifikasyon göndermek gerekli.

        """

        izin_form_data = self.input['form']
        # gereksiz form alanlarını sil
        if 'ileri' in izin_form_data:
            del izin_form_data['ileri']

        self.current.task_data['izin_form_data'] = izin_form_data
        izin_form = Form.objects.get(ad="İzin Formu")
        form_data = FormData()
        form_data.form = izin_form
        form_data.user = self.current.user
        form_data.data = json.dumps(izin_form_data)
        form_data.date = date.today()
        form_data.save()
        self.current.task_data['izin_form_data_key'] = form_data.key

    def izin_basvuru_kayit_bilgi_goster(self):
        """Personele izin başvuru kayıt sonucu bilgisini gösteren methoddur.

        """
        izin_basvuru = self.current.task_data['izin_form_data']
        izin_baslangic = izin_basvuru['izin_baslangic']
        izin_bitis = izin_basvuru['izin_bitis']
        self.current.output['msgbox'] = {
            'type': 'info', "title": 'İzin Başvurusu Yapıldı',
            "msg": '%s %s tarih aralığı için yaptığınız izin talebi başarıyla alınmıştır.' % (
                izin_baslangic, izin_bitis)
        }

    def izin_basvuru_goster(self):
        """Personel İşleri Dairesinde bulunan yetkili personele daha önce yapılmış olan izin
        başvurusunu gösteren methoddur. `IzinBasvuruForm` temel alınarak üretilen formda önceki
        veriler `FormData` modeli üzerinden alınır. `FormData` modelinde `data` field'ı üzerinden
        JSON olarak kayıt edilmiş veriler Python nesnesine dönüştürülereki form içinde ilgili
        alanlara basılır.

        """
        form_data = FormData.objects.get(self.current.task_data['izin_form_data_key'])
        basvuru_data = json.loads(form_data.data)

        _form = self.IzinBasvuruForm(current=self.current, title="İzin Talep Önizleme Formu")
        _form.personel_ad_soyad = fields.String("İzin Talep Eden")
        _form.personel_gorev = fields.String("Görevi")
        _form.personel_sicil_no = fields.String("Sicil no")
        _form.personel_birim = fields.String("Birimi")
        _form.yol_izni = fields.Boolean("Yol İzni")
        _form.kalan_izin = fields.Integer("Toplam Kalan İzin Süresi(Gün)")
        _form.toplam_izin_gun = fields.Integer("Kullanacağı İzin Süresi(Gün)")
        _form.toplam_kalan_izin = fields.Integer("Kalan İzin Süresi(Gün)")

        _form.ileri = fields.Button("Onayla")
        self.form_out(_form)

    def izin_basvuru_sonuc_kaydet(self):
        """Onay verilen izin başvuru sonucu kaydını gerçekleştiren methoddur.
        TODO : İzin başvurusu yapan personele notifikasyon gönderilmeli.
        TODO : Personele vekalet edecek kişinin seçimi yapılmalı

        """
        from datetime import date
        personel = Personel.objects.get(self.current.task_data['izin_personel_key'])
        form = self.input['form']
        izin = Izin()
        izin.tip = form['izin_turu']
        izin.baslangic = form['izin_baslangic']
        izin.bitis = form['izin_bitis']
        izin.onay = date.today()
        izin.adres = form['izin_adres']
        izin.personel = personel
        izin.save()

    @form_modifier
    def basvuru_form_inline_edit(self, serialized_form):
        """izin_basvuru_goster aşamasında personelin `IzinBasvuruForm` seçimlerini populate etmek
        için kullanılan methoddur.

        """
        if 'izin_turu' in serialized_form['schema'][
            'properties'] and self.current.task_data.has_key('izin_form_data_key'):
            # FormData modelindeki kayıtlar alınır
            form_data = FormData.objects.get(self.current.task_data['izin_form_data_key'])
            basvuru_data = json.loads(form_data.data)

            # izin başvurusu yapan personeli ve kadro özelliklerini bul
            form_personel = form_data.user.personel
            self.current.task_data['izin_personel_key'] = form_personel.key

            personel_atama = Atama.objects.get(personel=form_personel)

            # forma personelin görevi eklenir
            try:
                x = dict(personel_atama.kadro.get_choices_for("unvan_kod"))
                personel_gorev = x[personel_atama.kadro.unvan_kod]
                serialized_form['model']['personel_gorev'] = personel_gorev
            except Exception as e:
                pass

            # forma personelin sicil nosu eklenir
            try:
                personel_sicil_no = personel_atama.kurum_sicil_no
                serialized_form['model']['personel_sicil_no'] = personel_sicil_no
            except Exception as e:
                pass

            # forma personelin birim adı işlenir
            try:
                personel_birim = form_personel.birim.name
                serialized_form['model']['personel_birim'] = personel_birim
            except Exception as e:
                pass

            # İznin başlangıç ve bitiş tarihleri arasındaki gün sayısı hesaplanır
            # TODO: Formda tarih değişince js ile tekrar hesaplatmak lazım
            date_format = "%d.%m.%Y"
            a = datetime.strptime(basvuru_data['izin_baslangic'], date_format)
            b = datetime.strptime(basvuru_data['izin_bitis'], date_format)
            delta = b - a

            # formun verileri doldurulur
            serialized_form['model']['izin_turu'] = basvuru_data['izin_turu']
            serialized_form['model']['izin_ait_yil'] = basvuru_data['izin_ait_yil']
            serialized_form['model']['izin_baslangic'] = basvuru_data['izin_baslangic']
            serialized_form['model']['izin_bitis'] = basvuru_data['izin_bitis']
            serialized_form['model']['izin_adres'] = basvuru_data['izin_adres']
            serialized_form['model']['toplam_izin_gun'] = delta.days
            serialized_form['model']['personel_ad_soyad'] = "%s %s" % (
                form_personel.ad, form_personel.soyad)
