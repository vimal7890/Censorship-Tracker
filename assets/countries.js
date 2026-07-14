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
    "Australia": "AU",
    "Brazil": "BR",
    "China": "CN",
    "Cuba": "CU",
    "Egypt": "EG",
    "Eritrea": "ER",
    "Gabon": "GA",
    "India": "IN",
    "Indonesia": "ID",
    "Iran": "IR",
    "Jordan": "JO",
    "Kyrgyzstan": "KG",
    "Malaysia": "MY",
    "Myanmar": "MM",
    "Nepal": "NP",
    "North Korea": "KP",
    "Pakistan": "PK",
    "Qatar": "QA",
    "Russia": "RU",
    "Somalia": "SO",
    "South Korea": "KR",
    "Sudan": "SD",
    "Syria": "SY",
    "Turkey": "TR",
    "Turkmenistan": "TM",
    "UAE": "AE",
    "UK": "GB",
    "Uzbekistan": "UZ",
    "Vietnam": "VN",

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

    // Subnational jurisdictions (aggregate under parent country on the map)
    "Mississippi": { iso: "US", subnational: true, note: "U.S. state law" }
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
