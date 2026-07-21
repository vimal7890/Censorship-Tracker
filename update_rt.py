import json
import re

csv_entries = """Russia Today,Australia,March 2022,complete,"Banned and broadcasts suspended following the invasion of Ukraine.",https://www.theguardian.com/media/2022/mar/01/foxtel-and-sbs-suspend-russia-today-broadcasts-in-australia
Russia Today,Austria,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Belgium,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Bulgaria,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Canada,March 2022,complete,"The CRTC removed RT from the list of non-Canadian programming services.",https://www.canada.ca/en/radio-television-telecommunications/news/2022/03/crtc-removes-rt-and-rt-france-from-list-of-non-canadian-programming-services-and-stations-authorized-for-distribution.html
Russia Today,Croatia,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Cyprus,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Czech Republic,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Denmark,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Estonia,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Finland,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,France,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Germany,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Greece,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Hungary,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Ireland,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Italy,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Latvia,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Lithuania,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Luxembourg,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Malta,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Netherlands,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Poland,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Portugal,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Romania,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Slovakia,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Slovenia,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Spain,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,Sweden,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://www.consilium.europa.eu/en/press/press-releases/2022/03/02/eu-imposes-sanctions-on-state-owned-outlets-rt-russia-today-and-sputnik-s-broadcasting-in-the-eu/
Russia Today,United Kingdom,March 2022,complete,"Ofcom revoked RT's broadcast license and websites were blocked by major ISPs.",https://www.theguardian.com/media/2022/mar/18/ofcom-revokes-rt-broadcast-licence-russia-today
Russia Today,Ukraine,August 2014,complete,"Banned by Ukraine along with other Russian state-owned media following the annexation of Crimea.",https://www.theguardian.com/world/2014/aug/19/ukraine-bans-russian-tv-channels"""

with open("censorship_data.csv", "r") as f:
    content = f.read()

if not content.endswith("\n"):
    content += "\n"

with open("censorship_data.csv", "w") as f:
    f.write(content + csv_entries + "\n")

countries_to_add = {
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
    "Malta": "MT",
    "Poland": "PL",
    "Romania": "RO",
    "Slovakia": "SK",
    "Slovenia": "SI",
    "Sweden": "SE"
}

with open("assets/countries.js", "r") as f:
    countries_js = f.read()

# find "Vietnam": "VN",
pattern = r'("Vietnam": "VN",)'
insertion = ""
for country, code in countries_to_add.items():
    if f'"{country}":' not in countries_js:
        insertion += f'\n    "{country}": "{code}",'

new_js = re.sub(pattern, r'\1' + insertion, countries_js)

with open("assets/countries.js", "w") as f:
    f.write(new_js)

print("Done")
