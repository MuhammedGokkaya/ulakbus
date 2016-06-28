# -*-  coding: utf-8 -*-
# Copyright (C) 2015 ZetaOps Inc.
#
# This file is licensed under the GNU General Public License v3
# (GPLv3).  See LICENSE.txt for details.

"""Öğrenci Modülü

Bu modül Ulakbüs uygulaması için öğrenci modeli ve öğrenciyle ilişkili data modellerini içerir.

"""

from pyoko import Model, field
from .auth import Unit
from .ogrenci import Okutman
from ulakbus.lib.exceptions import DataConflictError

UYGUNLUK_DURUMU = [
    (1, "Uygun"),
    (2, "Mumkunse Uygun Degil"),
    (3, "Kesinlikle Uygun Degil")
]

HAFTA_ICI_GUNLER = [
    (1, "Pazartesi"),
    (2, "Sali"),
    (3, "Carsamba"),
    (4, "Persembe"),
    (5, "Cuma")
]

HAFTA_SONU_GUNLER = [
    (6, "Ctesi"),
    (7, "Pazar")
]

HAFTA = HAFTA_ICI_GUNLER + HAFTA_SONU_GUNLER


class GunZamanDilimleri(Model):
    """
        Belirtilen birimin, haftanin secilen bir gunune ait saat araligi belirler.

        Ornek:

            birim - Bilgisayar Muhendisligi Bolumu (Unit Nesnesi)
            gun - 1(Pazartesi)
            baslama_saat = '10'
            baslama_dakika = '30'
            bitis_saat = '12'
            bitis_dakika = '00'

        Bu ornege gore Bilgisayar Muhendisligi Bolumunde pazartesi gunu 10:30-12:00 saatleri arasi
        ders verilebilir. Bu belirlenen gune ait saat araliklari benzer olmamalidir. Eger cakisan
        saat veye saat araligi olursa ilgili model DataConflictError hatasi dondurur.
    """
    class Meta:
        unique_together = [('birim', 'gun', 'baslama_saat', 'baslama_dakika', 'bitis_saat', 'bitis_dakika')]
        search_fields = ['birim', 'gun', 'baslama_saat', 'bitis_saat']

    birim = Unit("Birim")
    gun = field.Integer("Gun", choices=HAFTA, index=True)
    baslama_saat = field.String("Baslama Saat", default='08', index=True)
    baslama_dakika = field.String("Baslama Dakika", default='00', index=True)
    bitis_saat = field.String("Bitis Saat", default='12', index=True)
    bitis_dakika = field.String("Bitis Dakika", default='00', index=True)

    def pre_save(self):
        """
        kayit baslama bitis zamani cakisiyor mu?
        """
        zaman_dilimleri = GunZamanDilimleri.objects.filter(birim=self.birim, gun=self.gun)

        for zaman in zaman_dilimleri:
            baslangic = int("%s%s" % (zaman.baslama_saat, zaman.baslama_dakika))
            bitis = int("%s%s" % (zaman.bitis_saat, zaman.bitis_dakika))

            yeni_baslangic = int("%s%s" % (self.baslama_saat, self.baslama_dakika))
            yeni_bitis = int("%s%s" % (self.bitis_saat, self.bitis_dakika))

            if yeni_baslangic > yeni_bitis:
                raise DataConflictError("Baslangic zamani bitis zamanindan buyuk olamaz.")

            if not ((yeni_baslangic < baslangic and yeni_bitis <= baslangic) or
                    (yeni_baslangic >= bitis and yeni_bitis > bitis)):
                raise DataConflictError("Baslangic bitis zamanlari onceki kayitlar ile cakismaktadir.")

    def __unicode__(self):
        return '%s - %s:%s' % (self.gun, self.baslama_saat, self.baslama_dakika)


class OgElemaniZamanPlani(Model):
    """
        Okutman, birim ve okutmanin ilgili birimde verecegi  haftalik ders saati bilgisi tutulur.
    """

    class Meta:
        verbose_name = 'Ogretim Elemani Zaman Kaydi'
        verbose_name_plural = 'Ogretim Elemanlari Zaman Kaydi'
        unique_together = [('okutman', 'birim')]
        search_fields = ['okutman', 'birim']

    okutman = Okutman("Okutman")
    birim = Unit("Birim")
    toplam_ders_saati = field.Integer("Ogretim Elemani Toplam Ders Saati", index=True)

    def __unicode__(self):
        return '%s - %s' % (self.birim, self.okutman)


class ZamanCetveli(Model):
    """
        Ilgili birime ait belirlenen zaman dilimleri ders program koordinatoru tarafindan
        ogretim elemanlarin saat araliklarina gore durumlarini belirleyecegi model
    """
    class Meta:
        verbose_name = 'Zaman Cetveli'
        unique_together = [('zaman_dilimi', 'ogretim_elemani_zaman_plani')]
        search_fields = ['zaman_dilimi', 'ogretim_elemani_zaman_plani', 'birim']

    birim = Unit("Birim")
    zaman_dilimi = GunZamanDilimleri("Zaman Dilimi")
    durum = field.Integer("Uygunluk Durumu", choices=UYGUNLUK_DURUMU, default=1, index=True)
    ogretim_elemani_zaman_plani = OgElemaniZamanPlani("Ogretim Elemani")

    def __unicode__(self):
        return '%s - %s - %s' % (self.ogretim_elemani_zaman_plani, self.zaman_dilimi, self.durum)