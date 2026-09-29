<!-- BEGIN GENERATED: banner -->
[English](../../en/cli/errors.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega. Prije spajanja na bilo koji drugi poslužitelj, uključujući službeni katastar i zemljišne knjige Republike Hrvatske, provjerite imate li pravo koristiti taj poslužitelj i njegove podatke; to činite na vlastitu odgovornost. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.4.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Što znače poruke o greškama

Kada nešto ne uspije, alat staje i ispisuje jedan redak crvenom bojom. Ova
stranica ispisuje te poruke i kaže što učiniti kod svake.

<!-- BEGIN GENERATED: errors -->
Svaka greška počinje ovom oznakom i jednom od poruka u nastavku:

```text
✗ Greška:
```

| Što alat ispisuje | Vrsta problema |
|---|---|
| **Greška veze** | `connection` |
| **Isteklo je vrijeme zahtjeva** | `timeout` |
| **Prekoračeno ograničenje broja zahtjeva** | `rate_limit` |
| **Neispravan odgovor poslužitelja** | `invalid_response` |
| **Čestica nije pronađena** | `parcel_not_found` |
| **Općina nije pronađena** | `municipality_not_found` |
| **Zemljišnoknjižni uložak nije pronađen** | `lr_unit_not_found` |
| **Posjedovni list nije pronađen** | `possession_sheet_not_found` |
| **Greška poslužitelja** | `server_error` |
| **Pristup odbijen** | `access_denied` |
| **HTTP greška** | `http_error` |
<!-- END GENERATED: errors -->

## Poruke o onome što ste upisali

**Čestica nije pronađena** znači da broj čestice ne postoji u općini koju ste
naveli. Provjerite broj na svom dokumentu, uključujući dio iza kose crte, i
provjerite jeste li naveli pravu općinu.

**Općina nije pronađena** znači da naziv ili šifra iza `-ko` nisu poznati.
Provjerite pravopis ili pronađite šifru naredbom
[traži-općinu](commands/search-municipality.md) i upotrijebite nju.

**Zemljišnoknjižni uložak nije pronađen** znači da broj uloška i glavna knjiga
koje ste zadali ne odgovaraju nijednom ulošku. Provjerite oba broja. Ako ste
krenuli od čestice, čestica možda još nije upisana u zemljišnu knjigu.

## Poruke o vezi

**Greška veze** znači da alat nije mogao doseći poslužitelj. Kod vježbe to znači
da probni poslužitelj na vašem računalu nije pokrenut. Zamolite osobu koja je
instalirala alat da ga pokrene, pa ponovno pokrenite naredbu.

**Isteklo je vrijeme zahtjeva** znači da poslužitelj nije odgovorio na vrijeme.
Pričekajte trenutak i ponovno pokrenite naredbu.

**Prekoračeno ograničenje broja zahtjeva** znači da su zahtjevi slani prebrzo.
Alat već razmiče svoje zahtjeve; pričekajte minutu i pokušajte ponovno.

**Greška poslužitelja** i **Neispravan odgovor poslužitelja** znače da je
poslužitelj odgovorio, ali ne na očekivani način. Pokušajte kasnije. Ako se
ponavlja, recite osobi koja je instalirala alat.

## Poruke samog Terminala

Ako Terminal odgovori `command not found`, alat nije instaliran za vaš račun ili
je Terminal otvoren prije nego što je instalacija završila. Zatvorite Terminal,
otvorite ga ponovno i pokušajte opet. Ako i dalje ne radi, obratite se osobi
koja je instalirala alat.

Ako alat ispiše `Nedostaje opcija` ili `Nepostojeća opcija`, dio naredbe je
pogrešno napisan. Usporedite svoj redak s primjerom na stranici te naredbe.
