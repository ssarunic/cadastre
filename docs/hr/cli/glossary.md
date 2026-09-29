<!-- BEGIN GENERATED: banner -->
[English](../../en/cli/glossary.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega. Prije spajanja na bilo koji drugi poslužitelj, uključujući službeni katastar i zemljišne knjige Republike Hrvatske, provjerite imate li pravo koristiti taj poslužitelj i njegove podatke; to činite na vlastitu odgovornost. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.4.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Pojmovnik

Riječi katastra i zemljišne knjige te gdje ih alat prikazuje. Pojmovi su
navedeni onako kako stoje na službenim ispravama.

| Pojam | Što znači | Gdje ga vidite u alatu |
|---|---|---|
| Katastarska čestica (k.č.) | Čestica: jedan numerirani dio zemljišta u katastru. | Broj čestice koji upisujete iza `pretraži`, `čestica` i `granica`. |
| Katastarska općina (k.o.) | Katastarska općina kojoj čestica pripada. Svaka ima naziv i matični broj, koji alat ispisuje kao šifru. | Vrijednost iza `-ko` u većini naredbi. [traži-općinu](commands/search-municipality.md) pronalazi matični broj. |
| Posjedovni list | Posjedovni list katastra: tko posjeduje česticu prema katastru. Nije dokaz vlasništva. | [posjedovni-list](commands/get-possession-sheet.md); [čestica](commands/get-parcel.md) uz `--posjednici`. |
| Posjednik | Posjednik upisan u katastru. | Reci posjedovnog lista na [čestica](commands/get-parcel.md). |
| Zemljišnoknjižni uložak (ZK uložak) | Sadrži pravno stanje nekretnine; vodi ga zemljišnoknjižni odjel općinskog suda. | [uložak](commands/get-lr-unit.md). Njegov broj pojavljuje se i na [čestica](commands/get-parcel.md), za jednu česticu ili za popis. |
| Čestica zgrade (zgr.) | Čestica starog katastra koja obuhvaća samo zgradu. Piše se `35/1 ZGR`, `35/1.ZGR` ili `zgr. 35/1`; nema vlastiti zemljišnoknjižni uložak. | Broj čestice u naredbama [get-parcel](commands/get-parcel.md) i [search](commands/search.md), ispisan kao `zgr. 35/1`. |
| Glavna knjiga | Svezak zemljišne knjige koji sadrži uloške jedne katastarske općine. | `--main-book` ili `--main-book-name` u naredbi [get-lr-unit](commands/get-lr-unit.md); [list-main-books](commands/list-main-books.md) pronalazi broj. |
| Knjiga položenih ugovora (KPU) | Zemljišnoknjižna knjiga za stanove i poslovne prostore prodane prije nego što je zgrada dobila zemljišnoknjižni uložak. | [list-books-of-dc](commands/list-books-of-dc.md). |
| Upis | Čin kojim je vlasnik, pravo ili zabilježba unesen u uložak. Upis svakog vlasnika prikazuje redni broj, datum zaprimanja i broj dnevnika. | Stupac Upis u vlastovnici naredbe [get-lr-unit](commands/get-lr-unit.md). |
| Posjedovnica (list A) | List A: čestice koje čine uložak. | Prva tablica iza zaglavlja uloška na [uložak](commands/get-lr-unit.md). |
| Vlastovnica (list B) | List B: vlasnici i njihovi udjeli. | `--vlasnici` na [uložak](commands/get-lr-unit.md). |
| Teretovnica (list C) | List C: založna prava (hipoteke), služnosti, stvarni tereti i zabilježbe. | `--tereti` na [uložak](commands/get-lr-unit.md). |
| Suvlasnički udio | Udio u suvlasništvu, zapisan kao razlomak, na primjer 1/2. | Stupac udjela lista B. |
| Plomba | Naznaka da je prijedlog za upis zaprimljen, a još nije riješen. Uložak se može promijeniti. | Redak s plombama na [uložak](commands/get-lr-unit.md); `--plombe` pokazuje o čemu je svaki prijedlog. |
| Dnevnik, broj Z | Dnevnik zemljišne knjige i poslovni broj (Z-broj) prijedloga za upis. | Zadnji broj dnevnika na [uložak](commands/get-lr-unit.md) i poslovni brojevi plombi. |
| Etažno vlasništvo | Vlasništvo posebnog dijela nekretnine (stana ili poslovnog prostora), povezano sa suvlasničkim dijelom cijele nekretnine. | Redak tipa uloška u zaglavlju uloška na [uložak](commands/get-lr-unit.md). |
| Kultura, način uporabe zemljišta | Način uporabe zemljišta upisan u katastru, na primjer oranica, pašnjak ili voćnjak. | Tablica načina uporabe na [čestica](commands/get-parcel.md). |
| OIB | Osobni identifikacijski broj fizičke ili pravne osobe. | Stupac OIB lista B, kada ga zemljišna knjiga ima. |
| Područni ured za katastar | Područni ured za katastar. | [uredi](commands/list-offices.md). |
| Granica čestice | Granica čestice zapisana koordinatama. | [granica](commands/get-geometry.md) i [preuzmi-gis](commands/download-gis.md). |
| HTRS96/TM (EPSG:3765) | Službeni koordinatni sustav Hrvatske, koristi se za sve granice. | Svaka koordinata koju alat ispiše. |
