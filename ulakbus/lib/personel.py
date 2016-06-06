# -*-  coding: utf-8 -*-
"""
"""
# Copyright (C) 2015 ZetaOps Inc.
#
# This file is licensed under the GNU General Public License v3
# (GPLv3).  See LICENSE.txt for details.

from dateutil.relativedelta import relativedelta
from pyoko.exceptions import ObjectDoesNotExist
import datetime

__author__ = 'Ali Riza Keles'


def gorunen_kademe_hesapla(derece, kademe):
    """
    Args:
        derece (int): personel derece
        kademe (int): personel kademe

    Returns:
        kademe (int): limite gore hesaplanmis kademe degeri
    """
    kademe_limitleri = {1: 4, 2: 6, 3: 8, 4: 9, 5: 9, 6: 9, 7: 9, 8: 9, 9: 9, 10: 9, 11: 9,
                        12: 9, 13: 9, 14: 9, 15: 9}
    try:
        kademe = kademe_limitleri[derece] if kademe > kademe_limitleri[derece] else kademe
        return kademe
    except KeyError:
        return 0


def derece_ilerlet(pkd, der, kad, terfi_tikanma):
    """
    Derece 3 kademede bir artar. Eger kademe 4 gelmise, derece 1 arttirilir
    Args:
        pkd (int): personel kadro derecesi
        der (int): derece
        kad (int): kademe

    Returns:
        der, kad: ilerletilmis derece ve kademe

    """
    if pkd < der:
        kad += 1
        if (not terfi_tikanma) & (kad == 4):
            kad = 1
            der -= 1
    return der, kad


def suren_terfi_var_mi(p):
    """
    Mevcut wfler icinde arama yaparak personel hakkinda, devam eden terfi isleminin
    olup olmadigi kontrol edilir.

    Args:
        p (str): personel key

    Returns:
        Devam eden islem varsa True, yoksa False

    """

    # TODO: wf ler icinde arama yap
    return False


def terfi_tarhine_gore_personel_listesi(baslangic_tarihi=None, bitis_tarihi=None,
                                        personel_turu=None, suren_terfi_kontrol=True):
    """
    Args:
        baslangic_tarihi (date): baslangic_tarihi
        bitis_tarihi (date): bitis_tarihi
        personel_turu (str): personel turu, 1 akademik, 2 idari
        suren_terfi_kontrol (bool): personel listesi hazirlanirken suren baska terfi islemi varmi
                                    kontrolunun yapilip yapilmayacagini kontrol eder.

    Returns:
        personeller (dict): personel kademe derece bilgileri iceren sozluk

    """

    from ulakbus.models.personel import Personel

    simdi = datetime.date.today()
    baslangic_tarihi = baslangic_tarihi or simdi
    bitis_tarihi = bitis_tarihi or simdi + datetime.timedelta(days=90)

    personeller = {}

    qs = Personel.objects.filter(personel_turu=personel_turu)

    terfisi_gelen_personeller = qs.or_filter(
        ga_sonraki_terfi_tarihi__range=[baslangic_tarihi, bitis_tarihi],
        kh_sonraki_terfi_tarihi__range=[baslangic_tarihi, bitis_tarihi],
        em_sonraki_terfi_tarihi__range=[baslangic_tarihi, bitis_tarihi]
    )

    for personel in terfisi_gelen_personeller:

        suren_terfi = False
        if suren_terfi_kontrol:
            suren_terfi = suren_terfi_var_mi(personel.key)

        if not suren_terfi_kontrol or not suren_terfi:
            # personel temel bilgileri
            p_data = {"key": personel.key, "tckn": personel.tckn, "ad": personel.ad,
                      "soyad": personel.soyad, "kadro_derece": personel.kadro.derece,
                      "suren_terfi": suren_terfi}

            # personel guncel derece ve kademeleri
            p_data.update(
                {
                    "guncel_gorev_ayligi_derece": personel.gorev_ayligi_derece,
                    "guncel_gorev_ayligi_kademe": personel.gorev_ayligi_kademe,
                    "guncel_kazanilmis_hak_derece": personel.kazanilmis_hak_derece,
                    "guncel_kazanilmis_hak_kademe": personel.kazanilmis_hak_kademe,
                    "guncel_emekli_muktesebat_derece": personel.emekli_muktesebat_derece,
                    "guncel_emekli_muktesebat_kademe": personel.emekli_muktesebat_kademe
                }
            )

            # personel guncel gorunen kademeleri
            p_data.update(
                {
                    "gorunen_gorev_ayligi_kademe": personel.gorunen_gorev_ayligi_kademe,
                    "gorunen_kazanilmis_hak_kademe": personel.gorunen_kazanilmis_hak_kademe,
                    "gorunen_emekli_muktesebat_kademe": personel.gorunen_emekli_muktesebat_kademe
                }
            )

            pkd = personel.kadro.derece

            # terfi sonrasi derece ve kademeler
            p_data["terfi_sonrasi_gorev_ayligi_derece"], p_data[
                "terfi_sonrasi_gorev_ayligi_kademe"] = derece_ilerlet(
                pkd,
                personel.gorev_ayligi_derece,
                personel.gorev_ayligi_kademe + 1)

            p_data["terfi_sonrasi_kazanilmis_hak_derece"], p_data[
                "terfi_sonrasi_kazanilmis_hak_kademe"] = derece_ilerlet(
                pkd,
                personel.kazanilmis_hak_derece,
                personel.kazanilmis_hak_kademe + 1)

            p_data["terfi_sonrasi_emekli_muktesebat_derece"], p_data[
                "terfi_sonrasi_emekli_muktesebat_kademe"] = derece_ilerlet(
                pkd,
                personel.gorev_ayligi_derece,
                personel.gorev_ayligi_kademe + 1)

            # terfi sonrasi gorunen kademeler
            p_data["terfi_sonrasi_gorunen_gorev_ayligi_kademe"] = gorunen_kademe_hesapla(
                p_data["terfi_sonrasi_gorev_ayligi_derece"],
                p_data["terfi_sonrasi_gorev_ayligi_kademe"])
            p_data["terfi_sonrasi_gorunen_kazanilmis_hak_kademe"] = gorunen_kademe_hesapla(
                p_data["terfi_sonrasi_kazanilmis_hak_derece"],
                p_data["terfi_sonrasi_kazanilmis_hak_kademe"])
            p_data["terfi_sonrasi_gorunen_emekli_muktesebat_kademe"] = gorunen_kademe_hesapla(
                p_data["terfi_sonrasi_emekli_muktesebat_derece"],
                p_data["terfi_sonrasi_emekli_muktesebat_kademe"])

            personeller[personel.key] = p_data

    return personeller

def terfi_durum_kontrol(personel_id):
    """
    :param personel_id:
    :return: terfi_kontrol (bool) : İlgili personelin terfisinin durup durmadığını belirtir.
    """

    from ulakbus.models import Personel, AskerlikKayitlari, UcretsizIzin

    personel = Personel.objects.get(personel_id)
    baslangic_tarih = datetime.date.today() - datetime.timedelta(days=1)
    bitis_tarih = datetime.date.today() + datetime.timedelta(days=1)
    askerlik_kontrol = False
    ucretsiz_izin_kontrol = False
    aday_memur_kontrol = False
    try:
        askerlik_kayit = AskerlikKayitlari.objects.get(
            personel_id = personel_id,
            baslama_tarihi__gte = baslangic_tarih,
            bitis_tarihi__lte = bitis_tarih
        )
    except ObjectDoesNotExist:
        askerlik_kontrol = True

    try:
        ucretsiz_izin = UcretsizIzin.objects.get(
            personel_id = personel_id,
            baslangic_tarih__gte = baslangic_tarih,
            bitis_tarihi__lte = bitis_tarih
        )
    except ObjectDoesNotExist:
        ucretsiz_izin_kontrol = True

    if not personel.aday_memur:
        aday_memur_kontrol = True

    # TODO : Personelin ceza durumu kontrol edilecek

    return (askerlik_kontrol and ucretsiz_izin_kontrol and aday_memur_kontrol)

def terfi_tikanma_kontrol(personel_id):

    from ulakbus.models import Personel

    personel = Personel.objects.get(personel_id)
    if personel.gorev_ayligi_derece == personel.kadro_derece:
        return True
    else:
        return False