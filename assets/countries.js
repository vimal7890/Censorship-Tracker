// Country names, aliases and map metadata generated from
// country_registry.json by build_countries.py. The same registry is
// validated against censorship_data.csv and vpn_data.json, and its
// ISO codes are used by build_timezones.py.
//
// Every name in the source datasets must resolve here. Subnational
// jurisdictions map to their parent ISO and are aggregated on the map.
window.COUNTRY_TO_ISO = {
    "Afghanistan": "AF",
    "Algeria": "DZ",
    "Australia": "AU",
    "Brazil": "BR",
    "People's Republic of China": "CN",
    "Cuba": "CU",
    "Egypt": "EG",
    "Eritrea": "ER",
    "Gabon": "GA",
    "India": "IN",
    "Indonesia": "ID",
    "Islamic Republic of Iran": "IR",
    "Israel": "IL",
    "Italy": "IT",
    "Jordan": "JO",
    "Kazakhstan": "KZ",
    "Kyrgyzstan": "KG",
    "Latvia": "LV",
    "Lebanon": "LB",
    "Malaysia": "MY",
    "Myanmar": "MM",
    "Nepal": "NP",
    "Netherlands": "NL",
    "New Zealand": "NZ",
    "North Korea": "KP",
    "Pakistan": "PK",
    "Philippines": "PH",
    "Qatar": "QA",
    "Russia": "RU",
    "Saudi Arabia": "SA",
    "Somalia": "SO",
    "South Korea": "KR",
    "Sudan": "SD",
    "Syria": "SY",
    "Tanzania": "TZ",
    "Türkiye": "TR",
    "Turkmenistan": "TM",
    "United Arab Emirates": "AE",
    "United Kingdom of Great Britain and Northern Ireland": "GB",
    "Ukraine": "UA",
    "United States of America": "US",
    "Uzbekistan": "UZ",
    "Venezuela": "VE",
    "Vietnam": "VN",
    "Austria": "AT",
    "Belgium": "BE",
    "Bulgaria": "BG",
    "Croatia": "HR",
    "Cyprus": "CY",
    "Czech Republic": "CZ",
    "Estonia": "EE",
    "Finland": "FI",
    "Germany": "DE",
    "Greece": "GR",
    "Hungary": "HU",
    "Ireland": "IE",
    "Lithuania": "LT",
    "Luxembourg": "LU",
    "Poland": "PL",
    "Romania": "RO",
    "Slovakia": "SK",
    "Slovenia": "SI",
    "Sweden": "SE",
    "Montenegro": "ME",
    "Albania": "AL",
    "North Macedonia": "MK",
    "Belarus": "BY",
    "Iraq": "IQ",
    "Oman": "OM",
    "France": "FR",
    "Denmark": "DK",
    "Spain": "ES",
    "Portugal": "PT",
    "Canada": "CA",
    "Mississippi": { iso: "US", subnational: true, note: "U.S. state law" },
    "Texas": { iso: "US", subnational: true, note: "U.S. state law" },
    "Crimea": { iso: "UA", subnational: true, note: "Disputed territory / trade controls" },
    "Andorra": "AD",
    "Antigua and Barbuda": "AG",
    "Bahrain": "BH",
    "Barbados": "BB",
    "Cape Verde": "CV",
    "Comoros": "KM",
    "Dominica": "DM",
    "Grenada": "GD",
    "Hong Kong": "HK",
    "Kiribati": "KI",
    "Liechtenstein": "LI",
    "Macau": "MO",
    "Maldives": "MV",
    "Malta": "MT",
    "Marshall Islands": "MH",
    "Mauritius": "MU",
    "Micronesia": "FM",
    "Monaco": "MC",
    "Nauru": "NR",
    "Palau": "PW",
    "Saint Kitts and Nevis": "KN",
    "Saint Lucia": "LC",
    "Saint Vincent and the Grenadines": "VC",
    "Samoa": "WS",
    "San Marino": "SM",
    "São Tomé and Príncipe": "ST",
    "Seychelles": "SC",
    "Singapore": "SG",
    "Tonga": "TO",
    "Tuvalu": "TV",
    "Vatican City": "VA",
    "Palestine": "PS",
    "Djibouti": "DJ",
    "Equatorial Guinea": "GQ",
    "South Africa": "ZA",
    "South Sudan": "SS",
    "Uganda": "UG",
    "Colombia": "CO",
    "Timor-Leste": "TL",
    "Niue": "NU",
    "Tokelau": "TK",
    "United Kingdom": "GB",
    "Greenland": "DK",
    "Sao Tome and Principe": "ST",
    "East Timor (Timor-Leste)": "TL"
};

window.COUNTRY_CANONICAL_NAMES = {
    AF: "Afghanistan",
    DZ: "Algeria",
    AU: "Australia",
    BR: "Brazil",
    CN: "People's Republic of China",
    CU: "Cuba",
    EG: "Egypt",
    ER: "Eritrea",
    GA: "Gabon",
    IN: "India",
    ID: "Indonesia",
    IR: "Islamic Republic of Iran",
    IL: "Israel",
    IT: "Italy",
    JO: "Jordan",
    KZ: "Kazakhstan",
    KG: "Kyrgyzstan",
    LV: "Latvia",
    LB: "Lebanon",
    MY: "Malaysia",
    MM: "Myanmar",
    NP: "Nepal",
    NL: "Netherlands",
    NZ: "New Zealand",
    KP: "North Korea",
    PK: "Pakistan",
    PH: "Philippines",
    QA: "Qatar",
    RU: "Russia",
    SA: "Saudi Arabia",
    SO: "Somalia",
    KR: "South Korea",
    SD: "Sudan",
    SY: "Syria",
    TZ: "Tanzania",
    TR: "Türkiye",
    TM: "Turkmenistan",
    AE: "United Arab Emirates",
    GB: "United Kingdom of Great Britain and Northern Ireland",
    UA: "Ukraine",
    US: "United States of America",
    UZ: "Uzbekistan",
    VE: "Venezuela",
    VN: "Vietnam",
    AT: "Austria",
    BE: "Belgium",
    BG: "Bulgaria",
    HR: "Croatia",
    CY: "Cyprus",
    CZ: "Czech Republic",
    EE: "Estonia",
    FI: "Finland",
    DE: "Germany",
    GR: "Greece",
    HU: "Hungary",
    IE: "Ireland",
    LT: "Lithuania",
    LU: "Luxembourg",
    PL: "Poland",
    RO: "Romania",
    SK: "Slovakia",
    SI: "Slovenia",
    SE: "Sweden",
    ME: "Montenegro",
    AL: "Albania",
    MK: "North Macedonia",
    BY: "Belarus",
    IQ: "Iraq",
    OM: "Oman",
    FR: "France",
    DK: "Denmark",
    ES: "Spain",
    PT: "Portugal",
    CA: "Canada",
    AD: "Andorra",
    AG: "Antigua and Barbuda",
    BH: "Bahrain",
    BB: "Barbados",
    CV: "Cape Verde",
    KM: "Comoros",
    DM: "Dominica",
    GD: "Grenada",
    HK: "Hong Kong",
    KI: "Kiribati",
    LI: "Liechtenstein",
    MO: "Macau",
    MV: "Maldives",
    MT: "Malta",
    MH: "Marshall Islands",
    MU: "Mauritius",
    FM: "Micronesia",
    MC: "Monaco",
    NR: "Nauru",
    PW: "Palau",
    KN: "Saint Kitts and Nevis",
    LC: "Saint Lucia",
    VC: "Saint Vincent and the Grenadines",
    WS: "Samoa",
    SM: "San Marino",
    ST: "São Tomé and Príncipe",
    SC: "Seychelles",
    SG: "Singapore",
    TO: "Tonga",
    TV: "Tuvalu",
    VA: "Vatican City",
    PS: "Palestine",
    DJ: "Djibouti",
    GQ: "Equatorial Guinea",
    ZA: "South Africa",
    SS: "South Sudan",
    UG: "Uganda",
    CO: "Colombia",
    TL: "Timor-Leste",
    NU: "Niue",
    TK: "Tokelau"
};

// Map-only territory aliases: data and dossiers stay keyed to the
// sovereign country while the SVG may still paint a separate outline.
window.MAP_ISO_ALIASES = {
    GL: "DK"
};

window.mapIsoOf = function (iso) {
    return (window.MAP_ISO_ALIASES || {})[iso] || iso;
};

window.mapPathsForIso = function (iso) {
    const paths = [iso];
    Object.entries(window.MAP_ISO_ALIASES || {}).forEach(([alias, parent]) => {
        if (parent === iso) paths.push(alias);
    });
    return paths;
};

// Territories with no path in assets/world.svg are drawn as markers.
// Coordinates are [longitude, latitude].
window.MICROSTATE_LATLON = {
    AD: [1.52, 42.51],
    AG: [-61.8, 17.06],
    BB: [-59.54, 13.19],
    BH: [50.55, 26.07],
    CV: [-23.61, 15.12],
    DM: [-61.37, 15.41],
    FM: [158.16, 6.92],
    GD: [-61.68, 12.12],
    HK: [114.17, 22.32],
    KI: [172.98, 1.33],
    KM: [43.33, -11.65],
    KN: [-62.73, 17.3],
    LC: [-60.98, 13.91],
    LI: [9.55, 47.14],
    MC: [7.42, 43.73],
    MH: [171.38, 7.09],
    MO: [113.55, 22.2],
    MT: [14.45, 35.9],
    MU: [57.55, -20.28],
    MV: [73.22, 3.2],
    NR: [166.93, -0.52],
    NU: [-169.87, -19.05],
    PW: [134.58, 7.51],
    SC: [55.45, -4.62],
    SG: [103.82, 1.35],
    SM: [12.46, 43.94],
    ST: [6.61, 0.19],
    TK: [-171.85, -9.2],
    TO: [-175.2, -21.18],
    TV: [179.2, -8.52],
    VA: [12.45, 41.9],
    VC: [-61.2, 13.25],
    WS: [-172.1, -13.76]
};

// world.svg is a plain spherical Mercator on a 1009x651 viewBox.
window.MAP_PROJECTION = { k: 160.58734, x0: 475.1309, y0: 463.6362 };

window.projectLonLat = function (lon, lat) {
    const { k, x0, y0 } = window.MAP_PROJECTION;
    let l = lon;
    while (l < -169.52) l += 360;
    while (l > 190.48) l -= 360;
    return {
        x: k * (l * Math.PI / 180) + x0,
        y: y0 - k * Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI / 180) / 2))
    };
};

// Resolve a display name or alias to its ISO code.
window.isoOf = function (name) {
    const v = window.COUNTRY_TO_ISO[name];
    return v && (v.iso || v);
};

// Resolve any recognized spelling to the registry's canonical display name.
window.canonicalCountryName = function (name) {
    const iso = window.isoOf(name);
    return iso && window.COUNTRY_CANONICAL_NAMES[iso];
};

window.isSubnational = function (name) {
    const v = window.COUNTRY_TO_ISO[name];
    return !!(v && v.subnational);
};

window.subnationalNote = function (name) {
    const v = window.COUNTRY_TO_ISO[name];
    return (v && v.note) || '';
};
