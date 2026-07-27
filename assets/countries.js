// Country display names (as they appear in censorship_data.csv, vpn_data.json
// and age_verification_data.json) mapped to ISO 3166-1 alpha-2 codes, which
// are the path ids used by assets/world.svg.
//
// Rules:
//  - Every distinct country/territory name in censorship_data.csv MUST have an
//    entry here (enforced by tests/test_world_map.py).
//  - Subnational jurisdictions (e.g. US states) map to their parent country
//    with `subnational: true`; they are aggregated under the parent on the map.
window.COUNTRY_TO_ISO = {
    "Afghanistan": "AF",
    "Algeria": "DZ",
    "Australia": "AU",
    "Brazil": "BR",
    "China": "CN",
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
    "Türkiye": "TR",
    "Turkmenistan": "TM",
    "United Arab Emirates": "AE",
    "United Kingdom": "GB",
    "Ukraine": "UA",
    "United States": "US",
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

    // Name variants used by vpn_data.json / age_verification_data.json
    "United Arab Emirates": "AE",
    "United Kingdom": "GB",
    "Belarus": "BY",
    "Iraq": "IQ",
    "Oman": "OM",
    "France": "FR",
    "Denmark": "DK",
    "Spain": "ES",
    "Portugal": "PT",
    "Canada": "CA",

    // Subnational / non-sovereign territories (aggregate under parent on the map).
    // Crimea has no separate path in world.svg — GitHub trade-control rows are
    // shown under Ukraine, with the territory name retained in the dossier.
    "Mississippi": { iso: "US", subnational: true, note: "U.S. state law" },
    "Texas": { iso: "US", subnational: true, note: "U.S. state law" },
    "Crimea": { iso: "UA", subnational: true, note: "Disputed territory / trade controls" },

    // Microstates and small island nations. These have no outline in
    // world.svg (see MICROSTATE_LATLON below) and are drawn as map markers.
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
    "Sao Tome and Principe": "ST",
    "Seychelles": "SC",
    "Singapore": "SG",
    "Tonga": "TO",
    "Tuvalu": "TV",
    "Vatican City": "VA"
};

// Territories with no path in assets/world.svg. The amCharts worldLow outline
// drops anything under roughly 1,000 km², which is every microstate and most
// small island nations — so Malta, Singapore, Bahrain, the Caribbean and
// Pacific states could be mapped to an ISO code but never shaded. index.html
// draws these as circular markers instead, positioned by projecting the
// coordinates below.
//
// [longitude, latitude], keyed by ISO 3166-1 alpha-2.
window.MICROSTATE_LATLON = {
    AD: [1.52, 42.51],     AG: [-61.80, 17.06],   BB: [-59.54, 13.19],
    BH: [50.55, 26.07],    CV: [-23.61, 15.12],   DM: [-61.37, 15.41],
    FM: [158.16, 6.92],    GD: [-61.68, 12.12],   HK: [114.17, 22.32],
    KI: [172.98, 1.33],    KM: [43.33, -11.65],   KN: [-62.73, 17.30],
    LC: [-60.98, 13.91],   LI: [9.55, 47.14],     MC: [7.42, 43.73],
    MH: [171.38, 7.09],    MO: [113.55, 22.20],   MT: [14.45, 35.90],
    MU: [57.55, -20.28],   MV: [73.22, 3.20],     NR: [166.93, -0.52],
    PW: [134.58, 7.51],    SC: [55.45, -4.62],    SG: [103.82, 1.35],
    SM: [12.46, 43.94],    ST: [6.61, 0.19],      TO: [-175.20, -21.18],
    TV: [179.20, -8.52],   VA: [12.45, 41.90],    VC: [-61.20, 13.25],
    WS: [-172.10, -13.76]
};

// world.svg is a plain spherical Mercator on a 1009x651 viewBox. These
// constants were fitted against the centroids of 24 countries that do have
// outlines in the file; the worst residual is under 2.5px, and they place the
// northern tip of Greenland within half a pixel of the top edge.
//
//   x = k * lon_radians + x0
//   y = y0 - k * ln(tan(PI/4 + lat_radians/2))
window.MAP_PROJECTION = { k: 160.58734, x0: 475.1309, y0: 463.6362 };

// Project [longitude, latitude] to world.svg user-space coordinates.
window.projectLonLat = function (lon, lat) {
    const { k, x0, y0 } = window.MAP_PROJECTION;
    // The map spans a full 360 degrees but starts at about 169.5W rather than
    // 180W, so Pacific longitudes just west of the antimeridian (Samoa, Tonga)
    // belong on the right-hand edge, not off the left one.
    let l = lon;
    while (l < -169.52) l += 360;
    while (l > 190.48) l -= 360;
    return {
        x: k * (l * Math.PI / 180) + x0,
        y: y0 - k * Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI / 180) / 2))
    };
};

// Resolve a display name to its ISO code (or undefined).
window.isoOf = function (name) {
    const v = window.COUNTRY_TO_ISO[name];
    return v && (v.iso || v);
};

// True when the display name is a subnational jurisdiction.
window.isSubnational = function (name) {
    const v = window.COUNTRY_TO_ISO[name];
    return !!(v && v.subnational);
};

// Optional note for a subnational / non-sovereign territory entry.
window.subnationalNote = function (name) {
    const v = window.COUNTRY_TO_ISO[name];
    return (v && v.note) || '';
};
