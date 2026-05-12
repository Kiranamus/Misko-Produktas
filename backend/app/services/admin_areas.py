COUNTY_BY_MUNICIPALITY = {
    "Alytaus m. sav.": "Alytaus apskritis",
    "Alytaus r. sav.": "Alytaus apskritis",
    "Druskininkų sav.": "Alytaus apskritis",
    "Lazdijų r. sav.": "Alytaus apskritis",
    "Varėnos r. sav.": "Alytaus apskritis",
    "Kauno m. sav.": "Kauno apskritis",
    "Kauno r. sav.": "Kauno apskritis",
    "Jonavos r. sav.": "Kauno apskritis",
    "Kaišiadorių r. sav.": "Kauno apskritis",
    "Kėdainių r. sav.": "Kauno apskritis",
    "Prienų r. sav.": "Kauno apskritis",
    "Birštono sav.": "Kauno apskritis",
    "Raseinių r. sav.": "Kauno apskritis",
    "Klaipėdos m. sav.": "Klaipėdos apskritis",
    "Klaipėdos r. sav.": "Klaipėdos apskritis",
    "Kretingos r. sav.": "Klaipėdos apskritis",
    "Skuodo r. sav.": "Klaipėdos apskritis",
    "Šilutės r. sav.": "Klaipėdos apskritis",
    "Neringos sav.": "Klaipėdos apskritis",
    "Palangos m. sav.": "Klaipėdos apskritis",
    "Marijampolės sav.": "Marijampolės apskritis",
    "Vilkaviškio r. sav.": "Marijampolės apskritis",
    "Šakių r. sav.": "Marijampolės apskritis",
    "Kalvarijos sav.": "Marijampolės apskritis",
    "Kazlų Rūdos sav.": "Marijampolės apskritis",
    "Panevėžio r. sav.": "Panevėžio apskritis",
    "Biržų r. sav.": "Panevėžio apskritis",
    "Kupiškio r. sav.": "Panevėžio apskritis",
    "Pasvalio r. sav.": "Panevėžio apskritis",
    "Rokiškio r. sav.": "Panevėžio apskritis",
    "Panevėžio m. sav.": "Panevėžio apskritis",
    "Šiaulių m. sav.": "Šiaulių apskritis",
    "Šiaulių r. sav.": "Šiaulių apskritis",
    "Akmenės r. sav.": "Šiaulių apskritis",
    "Joniškio r. sav.": "Šiaulių apskritis",
    "Kelmės r. sav.": "Šiaulių apskritis",
    "Pakruojo r. sav.": "Šiaulių apskritis",
    "Radviliškio r. sav.": "Šiaulių apskritis",
    "Tauragės r. sav.": "Tauragės apskritis",
    "Šilalės r. sav.": "Tauragės apskritis",
    "Jurbarko r. sav.": "Tauragės apskritis",
    "Pagėgių sav.": "Tauragės apskritis",
    "Telšių r. sav.": "Telšių apskritis",
    "Mažeikių r. sav.": "Telšių apskritis",
    "Plungės r. sav.": "Telšių apskritis",
    "Rietavo sav.": "Telšių apskritis",
    "Utenos r. sav.": "Utenos apskritis",
    "Molėtų r. sav.": "Utenos apskritis",
    "Ignalinos r. sav.": "Utenos apskritis",
    "Zarasų r. sav.": "Utenos apskritis",
    "Visagino sav.": "Utenos apskritis",
    "Anykščių r. sav.": "Utenos apskritis",
    "Vilniaus m. sav.": "Vilniaus apskritis",
    "Vilniaus r. sav.": "Vilniaus apskritis",
    "Elektrėnų sav.": "Vilniaus apskritis",
    "Trakų r. sav.": "Vilniaus apskritis",
    "Ukmergės r. sav.": "Vilniaus apskritis",
    "Širvintų r. sav.": "Vilniaus apskritis",
    "Šalčininkų r. sav.": "Vilniaus apskritis",
    "Švenčionių r. sav.": "Vilniaus apskritis",
}


def normalize_municipality_name(municipality: str | None) -> str | None:
    if municipality is None:
        return None
    normalized = str(municipality).strip().strip('"')
    normalized = " ".join(normalized.split())
    return normalized or None


def county_for_municipality(municipality: str | None) -> str | None:
    normalized = normalize_municipality_name(municipality)
    if not normalized:
        return None
    return COUNTY_BY_MUNICIPALITY.get(normalized)
