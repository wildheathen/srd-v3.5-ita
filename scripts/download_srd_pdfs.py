#!/usr/bin/env python3
"""
Download all SRD 3.5 Italian PDFs from editorifolli.it.
Organizes by chapter directory. Resume-safe (skips existing files).

Usage:
  python scripts/download_srd_pdfs.py [--output-dir /tmp/srd-pdf-ita]
"""
import os
import sys
import time
import argparse
import subprocess

BASE_URL = "https://www.editorifolli.it/f/srd35/"

# Chapter mapping: prefix -> directory name
CHAPTERS = {
    "01": "01-regole-base",
    "02": "02-razze",
    "03": "03-classi",
    "04": "04-abilita",
    "05": "05-talenti",
    "06": "06-equipaggiamento",
    "07": "07-avventura",
    "08": "08-combattimento",
    "09": "09-magia",
    "10": "10-incantesimi",
}

# Complete manifest of all 249 PDFs
MANIFEST = [
    # 01 - Regole base (6)
    "srd35_01_01_basi.pdf",
    "srd35_01_02_caratteristiche.pdf",
    "srd35_01_03_allineamento.pdf",
    "srd35_01_04_statistichebase.pdf",
    "srd35_01_06_glossario.pdf",
    "srd35_01_08_puntiazione.pdf",
    # 02 - Razze: introduzione (1)
    "srd35_02_01_razze_introduzione.pdf",
    # 02 - Razze: individuali (107)
    "srd35_02_01_razze_aasimar.pdf",
    "srd35_02_01_razze_arcontisegugio.pdf",
    "srd35_02_01_razze_azer.pdf",
    "srd35_02_01_razze_bugbear.pdf",
    "srd35_02_01_razze_centauri.pdf",
    "srd35_02_01_razze_coboldi.pdf",
    "srd35_02_01_razze_coboldi_acquatici.pdf",
    "srd35_02_01_razze_coboldi_artici.pdf",
    "srd35_02_01_razze_coboldi_deserto.pdf",
    "srd35_02_01_razze_coboldi_giungla.pdf",
    "srd35_02_01_razze_coboldi_terra.pdf",
    "srd35_02_01_razze_doppelganger.pdf",
    "srd35_02_01_razze_elfi.pdf",
    "srd35_02_01_razze_elfi_acquatici.pdf",
    "srd35_02_01_razze_elfi_artici.pdf",
    "srd35_02_01_razze_elfi_boschi.pdf",
    "srd35_02_01_razze_elfi_deserto.pdf",
    "srd35_02_01_razze_elfi_drow.pdf",
    "srd35_02_01_razze_elfi_fuoco.pdf",
    "srd35_02_01_razze_elfi_giungla.pdf",
    "srd35_02_01_razze_elfi_grigi.pdf",
    "srd35_02_01_razze_elfi_mare.pdf",
    "srd35_02_01_razze_elfi_selvaggi.pdf",
    "srd35_02_01_razze_faen.pdf",
    "srd35_02_01_razze_felinidi.pdf",
    "srd35_02_01_razze_gargoyle.pdf",
    "srd35_02_01_razze_genasi_acqua.pdf",
    "srd35_02_01_razze_genasi_aria.pdf",
    "srd35_02_01_razze_genasi_fuoco.pdf",
    "srd35_02_01_razze_genasi_terra.pdf",
    "srd35_02_01_razze_geni_jann.pdf",
    "srd35_02_01_razze_giganti_colline.pdf",
    "srd35_02_01_razze_giganti_custodi.pdf",
    "srd35_02_01_razze_giganti_pietre.pdf",
    "srd35_02_01_razze_gith_yan.pdf",
    "srd35_02_01_razze_gith_zen.pdf",
    "srd35_02_01_razze_gnoll.pdf",
    "srd35_02_01_razze_gnomi.pdf",
    "srd35_02_01_razze_gnomi_acquatici.pdf",
    "srd35_02_01_razze_gnomi_aria.pdf",
    "srd35_02_01_razze_gnomi_artici.pdf",
    "srd35_02_01_razze_gnomi_deserto.pdf",
    "srd35_02_01_razze_gnomi_foreste.pdf",
    "srd35_02_01_razze_gnomi_giungla.pdf",
    "srd35_02_01_razze_gnomi_pensatori.pdf",
    "srd35_02_01_razze_gnomi_profondita.pdf",
    "srd35_02_01_razze_goblin.pdf",
    "srd35_02_01_razze_goblin_acquatici.pdf",
    "srd35_02_01_razze_goblin_aria.pdf",
    "srd35_02_01_razze_goblin_artici.pdf",
    "srd35_02_01_razze_goblin_deserto.pdf",
    "srd35_02_01_razze_goblin_giungla.pdf",
    "srd35_02_01_razze_grimlock.pdf",
    "srd35_02_01_razze_halfling.pdf",
    "srd35_02_01_razze_halfling_acqua.pdf",
    "srd35_02_01_razze_halfling_acquatici.pdf",
    "srd35_02_01_razze_halfling_artici.pdf",
    "srd35_02_01_razze_halfling_cuoreforte.pdf",
    "srd35_02_01_razze_halfling_deserto.pdf",
    "srd35_02_01_razze_halfling_giungla.pdf",
    "srd35_02_01_razze_halfling_profondita.pdf",
    "srd35_02_01_razze_halfling_spilungoni.pdf",
    "srd35_02_01_razze_halfling_spiriti.pdf",
    "srd35_02_01_razze_hobgoblin.pdf",
    "srd35_02_01_razze_hobgoblin_fuoco.pdf",
    "srd35_02_01_razze_kender.pdf",
    "srd35_02_01_razze_litoriani.pdf",
    "srd35_02_01_razze_lucertoloidi.pdf",
    "srd35_02_01_razze_marinidi.pdf",
    "srd35_02_01_razze_mezzelfi.pdf",
    "srd35_02_01_razze_mezzelfi_acquatici.pdf",
    "srd35_02_01_razze_mezzelfi_artici.pdf",
    "srd35_02_01_razze_mezzelfi_deserto.pdf",
    "srd35_02_01_razze_mezzelfi_fuoco.pdf",
    "srd35_02_01_razze_mezzelfi_giungla.pdf",
    "srd35_02_01_razze_mezzogre.pdf",
    "srd35_02_01_razze_mezzorchi.pdf",
    "srd35_02_01_razze_mezzorchi_acqua.pdf",
    "srd35_02_01_razze_mezzorchi_acquatici.pdf",
    "srd35_02_01_razze_mezzorchi_artici.pdf",
    "srd35_02_01_razze_mezzorchi_deserto.pdf",
    "srd35_02_01_razze_mezzorchi_giungla.pdf",
    "srd35_02_01_razze_mezzovistani.pdf",
    "srd35_02_01_razze_minotauri.pdf",
    "srd35_02_01_razze_minotauri_umanoidi.pdf",
    "srd35_02_01_razze_mojh.pdf",
    "srd35_02_01_razze_nani.pdf",
    "srd35_02_01_razze_nani_acquatici.pdf",
    "srd35_02_01_razze_nani_artici.pdf",
    "srd35_02_01_razze_nani_deserto.pdf",
    "srd35_02_01_razze_nani_dorati.pdf",
    "srd35_02_01_razze_nani_duergar.pdf",
    "srd35_02_01_razze_nani_fosso.pdf",
    "srd35_02_01_razze_nani_giungla.pdf",
    "srd35_02_01_razze_nani_profondita.pdf",
    "srd35_02_01_razze_nani_scuri.pdf",
    "srd35_02_01_razze_nani_terra.pdf",
    "srd35_02_01_razze_ogre.pdf",
    "srd35_02_01_razze_ogre_alti.pdf",
    "srd35_02_01_razze_ogre_magi.pdf",
    "srd35_02_01_razze_orchi.pdf",
    "srd35_02_01_razze_orchi_acqua.pdf",
    "srd35_02_01_razze_orchi_acquatici.pdf",
    "srd35_02_01_razze_orchi_artici.pdf",
    "srd35_02_01_razze_orchi_deserto.pdf",
    "srd35_02_01_razze_orchi_giungla.pdf",
    "srd35_02_01_razze_rakshasa.pdf",
    "srd35_02_01_razze_satiri.pdf",
    "srd35_02_01_razze_scorticamente.pdf",
    "srd35_02_01_razze_serpentoidi.pdf",
    "srd35_02_01_razze_sibeccai.pdf",
    "srd35_02_01_razze_spiritelli_pixie.pdf",
    "srd35_02_01_razze_tiefling.pdf",
    "srd35_02_01_razze_trogloditi.pdf",
    "srd35_02_01_razze_troll.pdf",
    "srd35_02_01_razze_umani.pdf",
    "srd35_02_01_razze_umani_acquatici.pdf",
    # 02 - Razze: archetipi (10)
    "srd35_02_02_razze_celestiali.pdf",
    "srd35_02_02_razze_fantasmi.pdf",
    "srd35_02_02_razze_immondi.pdf",
    "srd35_02_02_razze_licantropi.pdf",
    "srd35_02_02_razze_lich.pdf",
    "srd35_02_02_razze_mezzi-celestiali.pdf",
    "srd35_02_02_razze_mezzi-draghi.pdf",
    "srd35_02_02_razze_mezzi-immondi.pdf",
    "srd35_02_02_razze_mostricomerazze.pdf",
    "srd35_02_02_razze_vampiri.pdf",
    # 03 - Classi (70+)
    "srd35_03_00_classi_bonusdiclasse.pdf",
    "srd35_03_00_classi_varianti_intro.pdf",
    "srd35_03_01_classi_animaprescelta.pdf",
    "srd35_03_01_classi_barbaro.pdf",
    "srd35_03_01_classi_barbaro_ramingo.pdf",
    "srd35_03_01_classi_barbaro_totemico.pdf",
    "srd35_03_01_classi_bardo.pdf",
    "srd35_03_01_classi_bardo_combattente.pdf",
    "srd35_03_01_classi_bardo_divino.pdf",
    "srd35_03_01_classi_bardo_divino_listaincantesimi.pdf",
    "srd35_03_01_classi_bardo_druidico.pdf",
    "srd35_03_01_classi_bardo_listaincantesimi.pdf",
    "srd35_03_01_classi_bardo_saggio.pdf",
    "srd35_03_01_classi_bardo_saggio_listaincantesimi.pdf",
    "srd35_03_01_classi_bardo_selvaggio.pdf",
    "srd35_03_01_classi_bardo_selvaggio_listaincantesimi.pdf",
    "srd35_03_01_classi_chierico.pdf",
    "srd35_03_01_classi_chierico_cenobita.pdf",
    "srd35_03_01_classi_chierico_cenobita_listaincantesimi.pdf",
    "srd35_03_01_classi_chierico_listaincantesimi.pdf",
    "srd35_03_01_classi_chierico_paladino.pdf",
    "srd35_03_01_classi_druido.pdf",
    "srd35_03_01_classi_druido_cacciatore.pdf",
    "srd35_03_01_classi_druido_listaincantesimi.pdf",
    "srd35_03_01_classi_druido_vendicatore.pdf",
    "srd35_03_01_classi_guerriero.pdf",
    "srd35_03_01_classi_guerriero_furtivo.pdf",
    "srd35_03_01_classi_guerriero_picchiatore.pdf",
    "srd35_03_01_classi_ladro.pdf",
    "srd35_03_01_classi_ladro_combattente.pdf",
    "srd35_03_01_classi_ladro_terreselvagge.pdf",
    "srd35_03_01_classi_mago.pdf",
    "srd35_03_01_classi_mago_compagno.pdf",
    "srd35_03_01_classi_mago_guerriero.pdf",
    "srd35_03_01_classi_mago_listaincantesimi.pdf",
    "srd35_03_01_classi_mago_specialista.pdf",
    "srd35_03_01_classi_mago_talenti.pdf",
    "srd35_03_01_classi_magocombattente.pdf",
    "srd35_03_01_classi_magocombattente_listaincantesimi.pdf",
    "srd35_03_01_classi_maresciallo.pdf",
    "srd35_03_01_classi_mistico.pdf",
    "srd35_03_01_classi_monaco.pdf",
    "srd35_03_01_classi_monaco_resistente.pdf",
    "srd35_03_01_classi_monaco_stilidicombattimento.pdf",
    "srd35_03_01_classi_nobile.pdf",
    "srd35_03_01_classi_paladino.pdf",
    "srd35_03_01_classi_paladino_combattente.pdf",
    "srd35_03_01_classi_paladino_dellaliberta.pdf",
    "srd35_03_01_classi_paladino_dellaliberta_listaincantesimi.pdf",
    "srd35_03_01_classi_paladino_furioso.pdf",
    "srd35_03_01_classi_paladino_listaincantesimi.pdf",
    "srd35_03_01_classi_paladino_ramingo.pdf",
    "srd35_03_01_classi_ranger.pdf",
    "srd35_03_01_classi_ranger_combattente.pdf",
    "srd35_03_01_classi_ranger_listaincantesimi.pdf",
    "srd35_03_01_classi_ranger_naturale.pdf",
    "srd35_03_01_classi_ranger_selvatico.pdf",
    "srd35_03_01_classi_ranger_urbano.pdf",
    "srd35_03_01_classi_ranger_urbano_listaincantesimi.pdf",
    "srd35_03_01_classi_stregone.pdf",
    "srd35_03_01_classi_stregone_compagno.pdf",
    "srd35_03_01_classi_stregone_dabattaglia.pdf",
    "srd35_03_01_classi_stregone_fattucchiere.pdf",
    "srd35_03_01_classi_stregone_fattucchiere_listaincantesimi.pdf",
    "srd35_03_01_classi_stregone_listaincantesimi.pdf",
    "srd35_03_02_classi_cavalcaturapaladino.pdf",
    "srd35_03_02_classi_compagnoanimale.pdf",
    "srd35_03_02_classi_famiglio.pdf",
    "srd35_03_03_classi_multiclasse.pdf",
    "srd35_03_04_classidiprestigio_intro.pdf",
    # 04 - Abilità (3)
    "srd35_04_01_abilita.pdf",
    "srd35_04_01_elencoabilita.pdf",
    "srd35_04_02_abilita_gradimassimi.pdf",
    # 05 - Talenti (6)
    "srd35_05_01_talenti.pdf",
    "srd35_05_01_talenti_bonusguerriero.pdf",
    "srd35_05_01_talenti_creazioneoggetto.pdf",
    "srd35_05_01_talenti_metamagia.pdf",
    "srd35_05_01_talenti_mostri.pdf",
    "srd35_05_01_talentielenco.pdf",
    # 06 - Equipaggiamento (4)
    "srd35_06_01_equipaggiamento.pdf",
    "srd35_06_01_equipaggiamento_armature.pdf",
    "srd35_06_01_equipaggiamento_armi.pdf",
    "srd35_06_01_equipaggiamento_merciservizi.pdf",
    # 07 - Avventura (4)
    "srd35_07_01_avventura_capacitaditrasporto.pdf",
    "srd35_07_01_avventura_condizioni.pdf",
    "srd35_07_01_avventura_esplorazione.pdf",
    "srd35_07_01_avventura_movimento.pdf",
    # 08 - Combattimento (7)
    "srd35_08_01_combattimento.pdf",
    "srd35_08_01_combattimento_azioni.pdf",
    "srd35_08_01_combattimento_feritemorte.pdf",
    "srd35_08_02_combattimento_attacchispeciali.pdf",
    "srd35_08_02_combattimento_azionispecialiiniziativa.pdf",
    "srd35_08_02_combattimento_modificatori.pdf",
    "srd35_08_02_combattimento_movimentoposizionedistanza.pdf",
    # 09 - Magia (5)
    "srd35_09_00_magia_intro.pdf",
    "srd35_09_01_magia_capacitaspeciali.pdf",
    "srd35_09_01_magia_descrizioneincantesimi.pdf",
    "srd35_09_01_magia_incantesimiarcani.pdf",
    "srd35_09_01_magia_incantesimidivini.pdf",
    # 10 - Incantesimi (16)
    "srd35_10_01_incantesimi_A.pdf",
    "srd35_10_01_incantesimi_B.pdf",
    "srd35_10_01_incantesimi_C.pdf",
    "srd35_10_01_incantesimi_D.pdf",
    "srd35_10_01_incantesimi_E.pdf",
    "srd35_10_01_incantesimi_F.pdf",
    "srd35_10_01_incantesimi_G.pdf",
    "srd35_10_01_incantesimi_HIJK.pdf",
    "srd35_10_01_incantesimi_L.pdf",
    "srd35_10_01_incantesimi_M.pdf",
    "srd35_10_01_incantesimi_NO.pdf",
    "srd35_10_01_incantesimi_PQ.pdf",
    "srd35_10_01_incantesimi_R.pdf",
    "srd35_10_01_incantesimi_S.pdf",
    "srd35_10_01_incantesimi_T.pdf",
    "srd35_10_01_incantesimi_UVWXYZ.pdf",
]


def get_chapter_dir(filename):
    """Map a PDF filename to its chapter directory."""
    # Extract chapter number from srd35_XX_...
    m = __import__('re').match(r'srd35_(\d+)_', filename)
    if m:
        return CHAPTERS.get(m.group(1), "other")
    return "other"


def download_all(output_dir):
    """Download all PDFs from the manifest."""
    os.makedirs(output_dir, exist_ok=True)

    # Count per chapter
    chapter_counts = {}
    for f in MANIFEST:
        ch = get_chapter_dir(f)
        chapter_counts[ch] = chapter_counts.get(ch, 0) + 1

    print(f"Manifest: {len(MANIFEST)} PDFs in {len(chapter_counts)} chapters")
    for ch, count in sorted(chapter_counts.items()):
        print(f"  {ch}: {count} files")
    print()

    downloaded = 0
    skipped = 0
    errors = []

    for i, filename in enumerate(MANIFEST, 1):
        chapter = get_chapter_dir(filename)
        chapter_dir = os.path.join(output_dir, chapter)
        os.makedirs(chapter_dir, exist_ok=True)

        output_path = os.path.join(chapter_dir, filename)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            skipped += 1
            continue

        url = BASE_URL + filename
        print(f"[{i}/{len(MANIFEST)}] Downloading {filename}...", end=" ", flush=True)

        try:
            result = subprocess.run(
                ['curl', '-sL', '-o', output_path, url],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode != 0:
                raise RuntimeError(f"curl failed: {result.stderr.strip()}")
            size = os.path.getsize(output_path)
            if size == 0:
                os.remove(output_path)
                raise RuntimeError("Empty file downloaded")
            print(f"{size:,} bytes")
            downloaded += 1
            time.sleep(0.3)  # Be polite
        except Exception as e:
            print(f"ERROR: {e}")
            errors.append((filename, str(e)))

    print(f"\nDone! Downloaded: {downloaded}, Skipped: {skipped}, Errors: {len(errors)}")
    if errors:
        print("Failed files:")
        for f, e in errors:
            print(f"  {f}: {e}")

    return len(errors) == 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download SRD 3.5 Italian PDFs')
    parser.add_argument('--output-dir', default='/tmp/srd-pdf-ita',
                        help='Output directory for PDFs (default: /tmp/srd-pdf-ita)')
    args = parser.parse_args()
    success = download_all(args.output_dir)
    sys.exit(0 if success else 1)
