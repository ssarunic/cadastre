<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/list-offices.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega. Prije spajanja na bilo koji drugi poslužitelj, uključujući službeni katastar i zemljišne knjige Republike Hrvatske, provjerite imate li pravo koristiti taj poslužitelj i njegove podatke; to činite na vlastitu odgovornost. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.4.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Popis katastarskih ureda

Prikazuje sve područne urede za katastar s njihovim brojevima. Broj vam treba da
biste ispisali općine nekog ureda.

## Kada vam ovo treba

- Želite znati koji je ured nadležan za neko područje.
- Druga naredba traži broj ureda, a vi ga ne znate.

## Prije nego počnete

Ništa. Ova naredba ne traži unos.

## Korak po korak

1. Otvorite Terminal.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   uz uredi
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output uz uredi -->
   ```text
   21 katastarskih ureda u Hrvatskoj:

   +------+------------------------------------------------------------+
   |   ID | Naziv                                                      |
   +======+============================================================+
   |   35 | PODRUČNI URED ZA KATASTAR KRAPINA                          |
   +------+------------------------------------------------------------+
   |  130 | PODRUČNI URED ZA KATASTAR ŠIBENIK                          |
   +------+------------------------------------------------------------+
   |  700 | GRADSKI URED ZA KATASTAR I GEODETSKE POSLOVE GRADA ZAGREBA |
   +------+------------------------------------------------------------+
   |  163 | PODRUČNI URED ZA KATASTAR PULA-POLA                        |
   +------+------------------------------------------------------------+
   |  122 | PODRUČNI URED ZA KATASTAR OSIJEK                           |
   +------+------------------------------------------------------------+
   |  141 | PODRUČNI URED ZA KATASTAR SPLIT                            |
   +------+------------------------------------------------------------+
   |  135 | PODRUČNI URED ZA KATASTAR VUKOVAR                          |
   +------+------------------------------------------------------------+
   |  114 | PODRUČNI URED ZA KATASTAR ZADAR                            |
   +------+------------------------------------------------------------+
   |  110 | PODRUČNI URED ZA KATASTAR SLAVONSKI BROD                   |
   +------+------------------------------------------------------------+
   |  106 | PODRUČNI URED ZA KATASTAR POŽEGA                           |
   +------+------------------------------------------------------------+
   |   91 | PODRUČNI URED ZA KATASTAR GOSPIĆ                           |
   +------+------------------------------------------------------------+
   |   67 | PODRUČNI URED ZA KATASTAR KOPRIVNICA                       |
   +------+------------------------------------------------------------+
   |   53 | PODRUČNI URED ZA KATASTAR KARLOVAC                         |
   +------+------------------------------------------------------------+
   |  171 | PODRUČNI URED ZA KATASTAR ČAKOVEC                          |
   +------+------------------------------------------------------------+
   |  100 | PODRUČNI URED ZA KATASTAR VIROVITICA                       |
   +------+------------------------------------------------------------+
   |   79 | PODRUČNI URED ZA KATASTAR RIJEKA                           |
   +------+------------------------------------------------------------+
   |   72 | PODRUČNI URED ZA KATASTAR BJELOVAR                         |
   +------+------------------------------------------------------------+
   |   24 | PODRUČNI URED ZA KATASTAR ZAGREB                           |
   +------+------------------------------------------------------------+
   |   61 | PODRUČNI URED ZA KATASTAR VARAŽDIN                         |
   +------+------------------------------------------------------------+
   |  165 | PODRUČNI URED ZA KATASTAR DUBROVNIK                        |
   +------+------------------------------------------------------------+
   |   43 | PODRUČNI URED ZA KATASTAR SISAK                            |
   +------+------------------------------------------------------------+
   ```
   <!-- END GENERATED: output -->

4. **ID** je broj ureda. Koristite ga uz `--ured` na stranici
   [općine](list-municipalities.md).

## Što možete odabrati

Da popis spremite u datoteku, dodajte `--oblik csv` i `--datoteka` s nazivom
datoteke:

```bash
uz uredi --oblik csv --datoteka offices.csv
```

<!-- BEGIN GENERATED: options -->
| Upišite | Što radi | Ako izostavite |
|---|---|---|
| `--oblik`, `-ob` | Format izlaza (`tablica`, `json`, `csv`) | Koristi se `tablica` |
| `--datoteka`, `-dt` `PUTANJA` | Spremi izlaz u datoteku | Ne koristi se |
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Ova naredba ne uspijeva samo kad alat ne može doseći probni poslužitelj. Poruka
je objašnjena na [stranici o greškama](../errors.md); zamolite osobu koja je
instalirala alat da pokrene poslužitelj.

## Povezane stranice

- [općine](list-municipalities.md) koristi broj ureda.
- [info](info.md) pokazuje s kojim poslužiteljem alat razgovara.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `uz uredi --help`:

```text
Uporaba: uz uredi [OPCIJE]

  Popis svih katastarskih ureda u Hrvatskoj.

  Primjer:
    uz uredi
    uz uredi --oblik json

Opcije:
  -ob, --oblik [tablica|json|csv]
                                  Format izlaza
  -dt, --datoteka PUTANJA         Spremi izlaz u datoteku
  --help                          Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
