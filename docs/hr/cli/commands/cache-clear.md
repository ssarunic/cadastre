<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/cache-clear.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega. Prije spajanja na bilo koji drugi poslužitelj, uključujući službeni katastar i zemljišne knjige Republike Hrvatske, provjerite imate li pravo koristiti taj poslužitelj i njegove podatke; to činite na vlastitu odgovornost. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.4.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Brisanje pohranjenih podataka o granicama

Briše podatke o granicama jedne općine, ili svih općina, s vašeg računala. Alat
će podatke ponovno preuzeti kada sljedeći put zatražite granicu.

## Kada vam ovo treba

- Granice općine su se promijenile i želite da alat dohvati aktualne podatke.
- Želite osloboditi prostor na disku.

## Prije nego počnete

Odlučite želite li ukloniti jednu općinu ili sve. Ništa drugo nije pogođeno:
pohranjeni podaci samo su kopija onoga što poslužitelj može ponovno poslati.

## Korak po korak

1. Otvorite Terminal.
2. Upišite sljedeći redak i pritisnite Enter. Zamijenite SAVAR općinom koju
   želite ukloniti.

   ```bash
   uz predmemorija obriši -ko SAVAR --bez-pitanja
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output uz predmemorija obriši -ko SAVAR --bez-pitanja -->
   ```text
   ✓ Očišćena općina 334979 (oslobođeno 0.7 KB)
   ```
   <!-- END GENERATED: output -->

4. Alat potvrđuje što je uklonio i koliko je prostora oslobodio.

## Što možete odabrati

`--bez-pitanja` preskače pitanje koje alat inače postavlja prije brisanja. Bez
njega alat traži potvrdu; upišite `y` i pritisnite Enter za nastavak, ili samo
pritisnite Enter da podatke zadržite.

Da biste uklonili sve, umjesto naziva općine upotrijebite `--sve`:

```bash
uz predmemorija obriši --sve
```

<!-- BEGIN GENERATED: options -->
| Upišite | Što radi | Ako izostavite |
|---|---|---|
| `--općina`, `-ko` `TEKST` | Očisti specifičnu općinu | Ne koristi se |
| `--sve`, `-sv` | Očisti svu predmemoriju | Nije uključeno |
| `--bez-pitanja`, `-bp` | Preskoči potvrdu | Nije uključeno |
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Ako navedete općinu koja nije pohranjena, alat vam to kaže i ne uklanja ništa:

<!-- BEGIN GENERATED: output uz predmemorija obriši -ko LUKA --bez-pitanja -->
```text
Općina 334731 nije u predmemoriji
```
<!-- END GENERATED: output -->

Ako ne navedete ni općinu ni `--sve`, vidjet ćete ovo:

<!-- BEGIN GENERATED: output uz predmemorija obriši -->
```text
✗ Greška: Potrebno je --municipality ili --all

Pokušajte: cadastral cache clear --help
```
<!-- END GENERATED: output -->

## Povezane stranice

- [predmemorija popis](cache-list.md) pokazuje što je pohranjeno prije nego što
  išta uklonite.
- [preuzmi-gis](download-gis.md) ponovno preuzima općinu.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `uz predmemorija obriši --help`:

```text
Uporaba: uz predmemorija obriši [OPCIJE]

  Brisanje predmemoriranih GIS podataka.

  Primjeri:
    uz predmemorija obriši --općina 334979
    uz predmemorija obriši --sve
    uz predmemorija obriši -ko SAVAR --bez-pitanja

Opcije:
  -ko, --općina TEKST  Očisti specifičnu općinu
  -sv, --sve           Očisti svu predmemoriju
  -bp, --bez-pitanja   Preskoči potvrdu
  --help               Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
