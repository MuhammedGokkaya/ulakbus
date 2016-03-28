# -*-  coding: utf-8 -*-

# Copyright (C) 2015 ZetaOps Inc.
#
# This file is licensed under the GNU General Public License v3
# (GPLv3).  See LICENSE.txt for details.

"""Öğrencilerin Genel Bilgileri ile ilgili İş Akışlarına ait
sınıf ve metotları içeren modüldür.

Kimlik Bilgileri, İletişim Bilgileri ve Önceki Eğitim Bilgileri gibi
iş akışlarının yürütülmesini sağlar.

"""

from collections import OrderedDict
from pyoko.exceptions import ObjectDoesNotExist
from pyoko import ListNode
from zengine.forms import fields
from zengine import forms
from zengine.views.crud import CrudView, form_modifier
from zengine.notifications import Notify
from ulakbus.services.zato_wrapper import MernisKimlikBilgileriGetir
from ulakbus.services.zato_wrapper import KPSAdresBilgileriGetir
from ulakbus.models.ogrenci import Ogrenci, OgrenciProgram, Program, Donem, DonemDanisman
from ulakbus.models.ogrenci import DegerlendirmeNot, DondurulmusKayit
from ulakbus.models.personel import Personel
from ulakbus.models.auth import Role, AbstractRole, Unit
from ulakbus.views.ders.ders import prepare_choices_for_model


class KimlikBilgileriForm(forms.JsonForm):
    """
    ``KimlikBilgileri`` sınıfı için form olarak kullanılacaktır. Form,
    include listesinde, aşağıda tanımlı alanlara sahiptir.

    """

    class Meta:
        include = ['tckn', "ad", "soyad", "cinsiyet", "dogum_tarihi", "dogum_yeri", "uyruk",
                   "medeni_hali", "baba_adi", "ana_adi",
                   "cuzdan_seri", "cuzdan_seri_no", "kayitli_oldugu_il", "kayitli_oldugu_ilce",
                   "kayitli_oldugu_mahalle_koy",
                   "kayitli_oldugu_cilt_no", "kayitli_oldugu_aile_sıra_no",
                   "kayitli_oldugu_sira_no", "kimlik_cuzdani_verildigi_yer",
                   "kimlik_cuzdani_verilis_nedeni", "kimlik_cuzdani_kayit_no",
                   "kimlik_cuzdani_verilis_tarihi"]

    kaydet = fields.Button("Kaydet", cmd="save")
    mernis_sorgula = fields.Button("Mernis Sorgula", cmd="mernis_sorgula")


class KimlikBilgileri(CrudView):
    """Kimlik Bilgileri İş Akışı

    Kimlik Bilgileri iş akışı 3 adımdan olusmaktadır.

    * Kimlik Bilgileri Formu
    * Mernis Kimlik Sorgulama
    * Kimlik Bilgileri Kaydet

    Bu iş akışımda kullanılan metotlar şu şekildedir:

    Kimlik Bilgilerini Listele:
        CrudView list metodu kullanılmıştır.Kimlik Bilgileri formunu
        listeler.

    Mernis'ten Kimlik Bilgilerini Getir:
        MERNİS, merkezi nüfus idare sisteminin kısa proje adıdır. Bu metot sayesinde
        öğrenciye ait kimlik bilgilerine MERNİS'ten erişilir. KimlikBilgileriForm'undaki
        alanlar MERNİS'ten gelen bilgiler doğrultusunda doldurulur.

    Kaydet:
        MERNİS'ten gelen bilgileri ve yetkili kişinin öğrenciyle girdiği bilgileri
        kaydeder. Bu adım ``CrudView.save()`` metodunu kullanır. İş akışı bu adımdan
        sonra sona erer.

    Bu sınıf ``CrudView`` extend edilerek hazırlanmıştır. Temel model ``Ogrenci``
    modelidir. Meta.model bu amaçla kullanılmıştır.

    Adımlar arası geçiş manuel yürütülmektedir.

    """

    class Meta:
        model = "Ogrenci"

    def kimlik_bilgileri(self):
        """Kimlik Bilgileri Formu"""

        self.form_out(KimlikBilgileriForm(self.object, current=self.current))

    def mernis_sorgula(self):
        """Mernis Sorgulama

        Zato wrapper metodlarıyla Mernis servisine bağlanır, servisten dönen
        değerlerle nesneyi doldurup kaydeder.

        """

        servis = MernisKimlikBilgileriGetir(tckn=self.object.tckn)
        kimlik_bilgisi = servis.zato_request()
        self.object(**kimlik_bilgisi)
        self.object.save()


class IletisimBilgileriForm(forms.JsonForm):
    """
    ``İletişimBilgileri`` sınıfı için form olarak kullanılacaktır. Form,
    include listesinde, aşağıda tanımlı alanlara sahiptir.

    """

    class Meta:
        include = ["ikamet_il", "ikamet_ilce", "ikamet_adresi", "adres2", "posta_kodu", "e_posta",
                   "e_posta2", "tel_no",
                   "gsm"]

    kaydet = fields.Button("Kaydet", cmd="save")
    kps_sorgula = fields.Button("KPS Sorgula", cmd="kps_sorgula")


class IletisimBilgileri(CrudView):
    """İletişim Bilgileri İş Akışı

   İletişim Bilgileri iş akışı 3 adımdan oluşmaktadır.

   * İletisim Bilgileri Formu
   * KPS Adres Sorgulama
   * Iletisim Bilgileri Kaydet

   Bu iş akışında kullanılan metotlar şu şekildedir.

   İletişim Bilgilerini Listele:
      CrudView list metodu kullanılmıştır. İletişim Bilgileri formunu
      listeler.

   KPS Adres Bilgilerini Getir:
      Bu metot sayesinde öğrenciye ait yerleşim yeri bilgilerine merkezi
      Kimlik Paylaşım Sistemi üzerinden erişilir.

      Iletişim Bilgileri formundaki alanlar KPS'ten gelen bilgiler
      doğrultusunda doldurulur.

    Kaydet:
      KPS'ten gelen bilgileri ya da yetkili kişinin öğrenciyle ilgili girdiği
      bilgileri kaydeder. Bu adım ``CrudView.save()`` metodunu kullanır.
      İş akışı bu adımdan sonra sona erer.

    Bu sınıf ``CrudView`` extend edilerek hazırlanmıştır. Temel model ``Ogrenci``
    modelidir. Meta.model bu amaçla kullanılmıştır.

    Adımlar arası geçiş manuel yürütülmektedir.

    """

    class Meta:
        model = "Ogrenci"

    def iletisim_bilgileri(self):
        """İletişim Bilgileri Formu"""

        self.form_out(IletisimBilgileriForm(self.object, current=self.current))

    def kps_sorgula(self):
        """KPS Sorgulama

        Zato wrapper metodlarıyla KPS servisine bağlanır, servisten dönen
        değerlerle nesneyi doldurup kaydeder.

        """
        servis = KPSAdresBilgileriGetir(tckn=self.object.tckn)
        iletisim_bilgisi = servis.zato_request()
        self.object(**iletisim_bilgisi)
        self.object.save()


class OncekiEgitimBilgileriForm(forms.JsonForm):
    """
    ``OncekiEgitimBilgileri`` sınıfı  için object form olarak kullanılacaktır. Form,
    include listesinde, aşağıda tanımlı alanlara sahiptir.

    """

    class Meta:
        include = ["okul_adi", "diploma_notu", "mezuniyet_yili"]

    kaydet = fields.Button("Kaydet", cmd="save")


class OncekiEgitimBilgileri(CrudView):
    """Önceki Eğitim Bilgileri İş Akışı

   Önceki Eğitim Bilgileri iş akışı 2 adımdan oluşmaktadır.

   * Önceki Eğitim Bilgileri Formu
   * Önceki Eğitim Bilgilerini Kaydet

   Bu iş akışında  kullanılan metotlar şu şekildedir:

   Önceki Eğitim Bilgileri Formunu Listele:
      CrudView list metodu kullanılmıştır. Önceki Eğitim Bilgileri formunu listeler.

   Kaydet:
      Girilen önceki eğitim bilgilerini kaydeder. Bu adım ``CrudView.save()`` metodunu kullanır.
      İş akışı bu adımdan sonra sona erer.

   Bu sınıf ``CrudView`` extend edilerek hazırlanmıştır. Temel model ``OncekiEgitimBilgisi``
   modelidir. Meta.model bu amaçla kullanılmıştır.

   Adımlar arası geçiş manuel yürütülmektedir.

    """

    class Meta:
        model = "OncekiEgitimBilgisi"

    def onceki_egitim_bilgileri(self):
        """Önceki Eğitim Bilgileri Formu"""

        self.form_out(OncekiEgitimBilgileriForm(self.object, current=self.current))


def ogrenci_bilgileri(current):
    """Öğrenci Genel Bilgileri

    Öğrenci Genel Bilgileri, öğrencilerin kendi bilgilerini görüntüledikleri
    tek adımlık bir iş akışıdır.

    Bu metod tek adımlık bilgi ekranı hazırlar.

    """

    current.output['client_cmd'] = ['show', ]
    ogrenci = Ogrenci.objects.get(user_id=current.user_id)

    # ordered tablo için OrderedDict kullanılmıştır.
    kimlik_bilgileri = OrderedDict({})
    kimlik_bilgileri.update({'Ad Soyad': "%s %s" % (ogrenci.ad, ogrenci.soyad)})
    kimlik_bilgileri.update({'Cinsiyet': ogrenci.cinsiyet})
    kimlik_bilgileri.update({'Kimlik No': ogrenci.tckn})
    kimlik_bilgileri.update({'Uyruk': ogrenci.tckn})
    kimlik_bilgileri.update({'Doğum Tarihi': '{:%d.%m.%Y}'.format(ogrenci.dogum_tarihi)})
    kimlik_bilgileri.update({'Doğum Yeri': ogrenci.dogum_yeri})
    kimlik_bilgileri.update({'Baba Adı': ogrenci.baba_adi})
    kimlik_bilgileri.update({'Anne Adı': ogrenci.ana_adi})
    kimlik_bilgileri.update({'Medeni Hali': ogrenci.medeni_hali})

    iletisim_bilgileri = {
        'Eposta': ogrenci.e_posta,
        'Telefon': ogrenci.tel_no,
        'Sitem Kullanıcı Adı': current.user.username
    }

    current.output['object'] = [
        {
            "title": "Kimlik Bilgileri",
            "type": "table",
            "fields": kimlik_bilgileri
        },
        {
            "title": "İletişim Bilgileri",
            "type": "table",
            "fields": iletisim_bilgileri
        }
    ]


class ProgramSecimForm(forms.JsonForm):
    """
    ``DanismanAtama`` sınıfı için form olarak kullanılacaktır.

    """

    sec = fields.Button("Seç")


class DanismanSecimForm(forms.JsonForm):
    """
    ``DanismanAtama`` sınıfı için form olarak kullanılacaktır.

    """

    sec = fields.Button("Kaydet")


class KayitDondurmaForm(forms.JsonForm):
    """
    ``KayitDondurma`` sınıfı için form olarak kullanılacaktır.

    """
    baslangic_tarihi = fields.Date('Kayıt Dondurma Başlangıç Tarihi')

    class Donemler(ListNode):
        secim = fields.Boolean(type="checkbox")
        donem = fields.String('Donem')
        key = fields.String('Key', hidden=True)
        aciklama = fields.String('Aciklama')

    sec = fields.Button("Kaydet")


class DanismanAtama(CrudView):
    """Danışman Atama

    Öğrencilere danışman atamalarının yapılmasını sağlayan workflowa ait
    metdodları barındıran sınıftır.

    """

    class Meta:
        model = "OgrenciProgram"

    def program_sec(self):
        """Program Seçim Adımı

        Programlar veritabanından çekilip, açılır menu içine
        doldurulur.

        """
        guncel_donem = Donem.objects.filter(guncel=True)[0]
        ogrenci_id = self.current.input['id']
        self.current.task_data['ogrenci_id'] = ogrenci_id
        self.current.task_data['donem_id'] = guncel_donem.key

        _form = ProgramSecimForm(current=self.current, title="Öğrenci Programı Seçiniz")
        _choices = prepare_choices_for_model(OgrenciProgram, ogrenci_id=ogrenci_id)
        _form.program = fields.Integer(choices=_choices)
        self.form_out(_form)

    def danisman_sec(self):
        program_id = self.current.input['form']['program']
        donem_id = self.current.task_data['donem_id']
        self.current.task_data['program_id'] = program_id

        program = OgrenciProgram.objects.get(program_id)

        _form = DanismanSecimForm(current=self.current, title="Danışman Seçiniz")
        _choices = prepare_choices_for_model(DonemDanisman, donem_id=donem_id,
                                             bolum=program.program.birim)
        _form.donem_danisman = fields.Integer(choices=_choices)
        self.form_out(_form)

    def danisman_kaydet(self):
        program_id = self.current.task_data['program_id']
        donem_danisman_id = self.input['form']['donem_danisman']

        o = DonemDanisman.objects.get(donem_danisman_id)
        personel = o.okutman.personel

        self.current.task_data['personel_id'] = personel.key

        ogrenci_program = OgrenciProgram.objects.get(program_id)
        ogrenci_program.danisman = personel
        ogrenci_program.save()

    def kayit_bilgisi_ver(self):
        ogrenci_id = self.current.task_data['ogrenci_id']
        personel_id = self.current.task_data['personel_id']

        ogrenci = Ogrenci.objects.get(ogrenci_id)
        personel = Personel.objects.get(personel_id)

        self.current.output['msgbox'] = {
            'type': 'info', "title": 'Danışman Ataması Yapıldı',
            "msg": '%s adlı öğrenciye %s adlı personel danışman olarak atandı' % (ogrenci, personel)
        }


class OgrenciMezuniyet(CrudView):
    """Öğrenci Mezuniyet

    Öğrencilerin mezuniyet işlemlerinin yapılmasını sağlayan workflowa ait
    metdodları barındıran sınıftır.

    """

    class Meta:
        model = "OgrenciProgram"

    def program_sec(self):
        """Program Seçim Adımı

        Programlar veritabanından çekilip, açılır menu içine
        doldurulur.

        """
        guncel_donem = Donem.objects.filter(guncel=True)[0]
        ogrenci_id = self.current.input['id']
        self.current.task_data['ogrenci_id'] = ogrenci_id
        self.current.task_data['donem_id'] = guncel_donem.key

        _form = ProgramSecimForm(current=self.current, title="Öğrenci Programı Seçiniz")
        _choices = prepare_choices_for_model(OgrenciProgram, ogrenci_id=ogrenci_id)
        _form.program = fields.Integer(choices=_choices)
        self.form_out(_form)

    def mezuniyet_kaydet(self):
        from ulakbus.lib.ogrenci import OgrenciHelper
        try:

            mn = OgrenciHelper()
            ogrenci_program = OgrenciProgram.objects.get(self.input['form']['program'])
            ogrenci_sinav_list = DegerlendirmeNot.objects.set_params(
                rows=1, sort='sinav_tarihi desc').filter(ogrenci=ogrenci_program.ogrenci)
            ogrenci_son_sinav = ogrenci_sinav_list[0]
            diploma_no = mn.diploma_notu_uret(ogrenci_program.ogrenci_no)
            ogrenci_program.diploma_no = diploma_no
            ogrenci_program.mezuniyet_tarihi = ogrenci_son_sinav.sinav.tarih
            ogrenci_program.save()

            bolum_adi = ogrenci_program.program.bolum_adi
            ogrenci_no = ogrenci_program.ogrenci_no
            ogrenci_adi = '%s %s' % (ogrenci_program.ogrenci.ad, ogrenci_program.ogrenci.soyad)

            self.current.output['msgbox'] = {
                'type': 'info', "title": 'Bir Hata Oluştu',
                "msg": '%s numaralı %s adlı öğrenci %s adlı bölümden %s diploma numarası ile mezun \
                edilmiştir' % (ogrenci_no, ogrenci_adi, bolum_adi, diploma_no)
            }

        except Exception as e:
            self.current.output['msgbox'] = {
                'type': 'warning', "title": 'Bir Hata Oluştu',
                "msg": 'Öğrenci Mezuniyet Kaydı Başarısız. Hata Kodu : %s' % (e.message)
            }


class KayitDondurma(CrudView):
    """Öğrenci Kayıt Dondurma

    Öğrencilerin kayıt donduruma işlemlerinin yapılmasını sağlayan workflowa ait
    metdodları barındıran sınıftır.

    """

    class Meta:
        model = "OgrenciProgram"

    def program_sec(self):
        """Program Seçim Adımı

        Programlar veritabanından çekilip, açılır menu içine
        doldurulur.

        """
        ogrenci_id = self.current.input['id']
        self.current.task_data['ogrenci_id'] = ogrenci_id

        _form = ProgramSecimForm(current=self.current, title="Öğrenci Programı Seçiniz")
        _choices = prepare_choices_for_model(OgrenciProgram, ogrenci_id=ogrenci_id)
        _form.program = fields.Integer(choices=_choices)
        self.form_out(_form)

    def donem_sec(self):
        baslangic_tarihi = False
        secim_durum = False
        aciklama_metin = ""
        try:
            ogrenci_program = OgrenciProgram.objects.get(self.input['form']['program'])
            self.current.task_data['ogrenci_program_id'] = ogrenci_program.key

            # Öğrenci en fazla 2 dönem için kaydını dondurabilir
            donemler = Donem.objects.set_params(sort='baslangic_tarihi desc', rows='2').filter()
            ogrenci_adi = '%s %s' % (ogrenci_program.ogrenci.ad, ogrenci_program.ogrenci.soyad)

            _form = KayitDondurmaForm(current=self.current, title="Lütfen Dönem Seçiniz")
            for donem in donemler:
                baslangic_tarihi = False
                secim_durum = False
                aciklama_metin = ""
                try:
                    dk = DondurulmusKayit.objects.get(ogrenci_program=ogrenci_program, donem=donem)
                    secim_durum = True
                    aciklama_metin = dk.aciklama
                    baslangic_tarihi = dk.baslangic_tarihi
                except ObjectDoesNotExist:
                    secim_durum = False
                    aciklama_metin = ""

                _form.Donemler(secim=secim_durum, donem=donem.ad, key=donem.key,
                               aciklama=aciklama_metin)

            if baslangic_tarihi:
                _form.baslangic_tarihi = baslangic_tarihi
            else:
                _form.baslangic_tarihi = fields.Date('Başlangıç Tarihi')

            self.form_out(_form)

        except Exception as e:
            self.current.output['msgbox'] = {
                'type': 'warning', "title": 'Bir Hata Oluştu',
                "msg": 'Hata Kodu : %s' % (e.message)
            }

    def ogrenci_kayit_dondur(self):
        """Öğrenci kayıt dondurma WF son aşamasıdır.

        ``DondurulmusKayit`` modelinde, seçilen her donem başına bir kayıt yaratılır.
        Öğrencinin ilgili program kaydında kayıt_dondurma alanı True olarak değiştirilir,
        Öğrencinin "Öğrenci" olan rolü, "Dondurulmuş Ogrenci" olarak değiştirilir.
        Öğrencinin danışmanına bilgi verilir.

        """
        ogrenci_program = OgrenciProgram.objects.get(self.current.task_data['ogrenci_program_id'])
        ogrenci = ogrenci_program.ogrenci
        donemler = self.current.input['form']['Donemler']
        baslangic_tarihi = self.current.input['form']['baslangic_tarihi']

        for donem in donemler:
            donem_kayit = Donem.objects.get(donem['key'])
            try:

                dk = DondurulmusKayit.objects.get(ogrenci_program=ogrenci_program,
                                                  donem=donem_kayit)
                dk.aciklama = donem['aciklama']
                dk.baslangic_tarihi = baslangic_tarihi
                dk.save()

            except ObjectDoesNotExist:
                dk = DondurulmusKayit()
                dk.ogrenci_program = ogrenci_program
                dk.donem = donem_kayit
                dk.aciklama = donem['aciklama']
                dk.baslangic_tarihi = baslangic_tarihi
                dk.save()

            except Exception as e:

                self.current.output['msgbox'] = {
                    'type': 'warning', "title": 'Bir Hata Oluştu',
                    "msg": 'Hata Kodu : %s' % (e.message)
                }

            try:
                abstract_role = AbstractRole.objects.get(name="dondurulmus_kayit")
                user = ogrenci.user
                unit = Unit.objects.get(yoksis_no=ogrenci_program.program.yoksis_no)
                current_role = Role.objects.get(user=user, unit=unit)
                current_role.abstract_role = abstract_role
                current_role.save()
                ogrenci_ad_soyad = "%s %s" % (ogrenci.ad, ogrenci.soyad)
                notify_message = '%s numaralı, %s adlı öğrencinin %s programındaki kaydı ' \
                                 'dondurulmuştur' % (ogrenci_program.ogrenci_no, ogrenci_ad_soyad,
                                                     ogrenci_program.program.adi)
            except Exception as e:

                self.current.output['msgbox'] = {
                    'type': 'warning', "title": 'Bir Hata Oluştu',
                    "msg": 'Öğrenci Rol Değişim Kaydı Başarısız. Hata Kodu : %s' % (e.message)
                }

            # öğrencinin danışmanına bilgilendirme geçilir
            try:
                danisman_key = ogrenci_program.danisman.user.key
                Notify(danisman_key).set_message(title="Öğrenci Kaydı Donduruldu",
                                                 msg=notify_message, typ=Notify.Message)
                self.current.output['msgbox'] = {
                    'type': 'info', "title": 'Öğrenci Kayıt Dondurma Başarılı',
                    "msg": '%s' % (notify_message)
                }
            except Exception as e:
                self.current.output['msgbox'] = {
                    'type': 'warning', "title": 'Bir Hata Oluştu',
                    "msg": 'Öğrenci Danışmanı Bilgilendirme Başarısız. Hata Kodu : %s' % (e.message)
                }

    @form_modifier
    def kayit_dondurma_list_form_inline_edit(self, serialized_form):
        """KayitDondurmaForm'da seçim ve açıklama alanlarına inline edit özelliği sağlayan method.

        """
        if 'Donemler' in serialized_form['schema']['properties']:
            serialized_form['inline_edit'] = ['secim', 'aciklama']
