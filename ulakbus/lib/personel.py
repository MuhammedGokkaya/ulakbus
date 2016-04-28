# -*-  coding: utf-8 -*-
"""
"""

# Copyright (C) 2015 ZetaOps Inc.
#
# This file is licensed under the GNU General Public License v3
# (GPLv3).  See LICENSE.txt for details.
import datetime

from ulakbus.models import Personel

__author__ = 'zops5'


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
    kademe = kademe_limitleri[derece] if kademe > kademe_limitleri[derece] else kademe
    return kademe


def derece_ilerlet(pkd, der, kad):
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
        if kad == 4:
            kad = 1
            der -= 1
    return der, kad


def suren_terfi_var_mi(p):
    return False


def terfi_tarhine_gore_personel_listesi(baslangic_tarihi=None, bitis_tarihi=None,
                                        suren_terfi_kontrol=True):
    """
    Args:
        baslangic_tarihi (date): baslangic_tarihi
        bitis_tarihi (date): bitis_tarihi

    Returns:
        personeller (dict): personel kademe derece bilgileri iceren sozluk

    """
    simdi = datetime.date.today()
    baslangic_tarihi = baslangic_tarihi or simdi
    bitis_tarihi = bitis_tarihi or simdi + datetime.timedelta(days=90)

    terfisi_gelen_personeller = Personel.objects.filter(
        sonraki_terfi_tarihi__gte=baslangic_tarihi,
        sonraki_terfi_tarihi__lte=bitis_tarihi)

    personeller = {}
    for personel in terfisi_gelen_personeller:

        suren_terfi = False
        if suren_terfi_kontrol:
            suren_terfi = suren_terfi_var_mi(personel)

        if not suren_terfi_kontrol or not suren_terfi:
            # personel temel bilgileri
            p_data = {"tckn": personel.tckn, "ad": personel.ad, "soyad": personel.soyad,
                      "kadro_derece": personel.kadro.derece, "suren_terfi": suren_terfi}

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
                "terfi_sonrasi_gorev_ayligi_kademe"] = derece_ilerlet(pkd,
                                                                      personel.gorev_ayligi_derece,
                                                                      personel.gorev_ayligi_kademe + 1)

            p_data["terfi_sonrasi_kazanilmis_hak_derece"], p_data[
                "terfi_sonrasi_kazanilmis_hak_kademe"] = derece_ilerlet(pkd,
                                                                        personel.kazanilmis_hak_derece,
                                                                        personel.kazanilmis_hak_kademe + 1)

            p_data["terfi_sonrasi_emekli_muktesebat_derece"], p_data[
                "terfi_sonrasi_emekli_muktesebat_kademe"] = derece_ilerlet(pkd,
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
