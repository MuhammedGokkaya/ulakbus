# -*-  coding: utf-8 -*-
"""
"""

# Copyright (C) 2015 ZetaOps Inc.
#
# This file is licensed under the GNU General Public License v3
# (GPLv3).  See LICENSE.txt for details.


from ulakbus.models import User, Personel
from zengine.lib.test_utils import BaseTestCase
from zengine.notifications.model import NotificationMessage
import time


class TestCase(BaseTestCase):
    terfi_red = True

    def test_terfisi_gelen_personel(self):
        """
        TODO: docstring eklenecek.
        """
        usr = User.objects.get(username='personel_isleri_1')
        self.prepare_client('/terfisi_gelen_personel_listesi', user=usr)
        self.client.post()
        idari_forms = {'baslangic_tarihi': '20.05.2016',
                       'bitis_tarihi': '30.05.2016',
                       'devam': 1,
                       'personel_turu': 2}
        resp = self.client.post(form=idari_forms)
        ter_gel_id_per = resp.json['forms']['model']['Personel']
        assert len(ter_gel_id_per) == 3

        idari_per_db = len(Personel.objects.filter(personel_turu=2))

        assert idari_per_db - len(ter_gel_id_per) == 17

        # Terfisi yapilacak personel onaya gonder
        resp = self.client.post(cmd='onaya_gonder', form={'Personel': ter_gel_id_per,
                                                          'kaydet': 1})

        assert resp.json['msgbox']['title'] == "Personeller Onay Icin Gonderildi!"
        self.client.set_path('/logout')

        time.sleep(1)

        # Personel terfi islemini reddet bolumu
        token, user = self.get_user_token('genel_sekreter_1')
        self.prepare_client('/terfisi_gelen_personel_listesi', user=user, token=token)
        resp = self.client.post()
        self.client.post(cmd="red_aciklamasi_yaz",
                         form={'Personel': resp.json['forms']['model']['Personel'],
                               'duzenle': 1})
        NotificationMessage.objects.filter().delete()
        resp = self.client.post(
            wf='terfisi_gelen_personel_listesi',
            form={'devam': 1, 'red_aciklama': "Reddedildi"}
        )

        assert resp.json['msgbox']['msg'] == "Talebiniz Basariyla iletildi."
        self.client.set_path('/logout')

        time.sleep(1)

        user = User.objects.get(username='personel_isleri_1')
        self.prepare_client('/terfisi_gelen_personel_listesi', user=user)
        token, user = self.get_user_token('personel_isleri_1')
        resp = self.client.post(token=token)
        ter_gel_id_per = resp.json['forms']['model']['Personel']
        NotificationMessage.objects.filter().delete()

        assert len(ter_gel_id_per) == 3

        # Terfisi yapilacak personel duzenle
        ter_gel_id_per[0]['sec'] = True
        ter_gel_id_per[2]['sec'] = True

        terfi_duz_forms = {'Personel': ter_gel_id_per,
                           'duzenle': 1}

        resp = self.client.post(cmd="terfi_liste_duzenle", form=terfi_duz_forms)

        resp.json['forms']['model']['Personel'][0]['yeni_gorev_ayligi_derece'] = 2
        resp.json['forms']['model']['Personel'][0]['yeni_gorev_ayligi_kademe'] = 8
        resp.json['forms']['model']['Personel'][0]['yeni_gorev_ayligi_gorunen'] = 8

        resp.json['forms']['model']['Personel'][1]['yeni_kazanilmis_hak_derece'] = 3
        resp.json['forms']['model']['Personel'][1]['yeni_kazanilmis_hak_kademe'] = 8
        resp.json['forms']['model']['Personel'][1]['yeni_kazanilmis_hak_gorunen'] = 8

        ter_gel_id_per = resp.json['forms']['model']['Personel']

        resp = self.client.post(cmd='kaydet', form={'Personel': ter_gel_id_per,
                                                    'devam': 1})

        ter_gel_id_per = resp.json['forms']['model']['Personel']

        assert ter_gel_id_per[0]['yeni_gorev_ayligi'] == '2/8(8)'
        assert ter_gel_id_per[2]['yeni_kazanilmis_hak'] == '3/8(8)'

        # Terfisi yapilacak personel onaya gonder
        resp = self.client.post(cmd='onaya_gonder', form={'Personel': ter_gel_id_per,
                                                          'kaydet': 1})

        assert resp.json['msgbox']['title'] == "Personeller Onay Icin Gonderildi!"
        self.client.set_path('/logout')

        time.sleep(1)

        self.personel_terfi_onay()

    def personel_terfi_onay(self):
        """
        TODO: docstring eklenecek..
        """
        # Personel terfi islemini onayla bolumu
        user = User.objects.get(username='genel_sekreter_1')
        self.prepare_client('/terfisi_gelen_personel_listesi', user=user)
        token, user = self.get_user_token('genel_sekreter_1')
        resp = self.client.post(token=token)
        assert len(resp.json['forms']['model']['Personel']) == 3
        NotificationMessage.objects.filter().delete()

        ter_gel_id_per = resp.json['forms']['model']['Personel']

        resp = self.client.post(cmd='terfi_yap', form={'Personel': ter_gel_id_per,
                                                       'kaydet': 1})

        assert resp.json['msgbox']['title'] == "Personel Terfi Islemi Onaylandi!"
        self.client.set_path('/logout')

        time.sleep(1)

        usr = User.objects.get(username='personel_isleri_1')
        msg = NotificationMessage.objects.filter(receiver=usr)[0]
        token = msg.url.split('/')[-1]
        self.prepare_client('/terfisi_gelen_personel_listesi', user=usr, token=token)
        resp = self.client.post()
        NotificationMessage.objects.filter().delete()

        assert resp.json['msgbox']['title'] == "Terfi İşlemleri Onay Belgesi!"
