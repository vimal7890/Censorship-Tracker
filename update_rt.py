csv_entries = """Russia Today,Australia,March 2022,complete,"Banned and broadcasts suspended following the invasion of Ukraine.",https://www.theguardian.com/media/2022/mar/01/foxtel-and-sbs-suspend-russia-today-broadcasts-in-australia
Russia Today,Austria,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Belgium,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Bulgaria,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Canada,March 2022,complete,"The CRTC removed RT from the list of non-Canadian programming services.",https://www.canada.ca/en/radio-television-telecommunications/news/2022/03/crtc-removes-rt-and-rt-france-from-list-of-non-canadian-programming-services-and-stations-authorized-for-distribution.html
Russia Today,Croatia,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Cyprus,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Czech Republic,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Denmark,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Estonia,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Finland,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,France,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Germany,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Greece,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Hungary,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Ireland,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Italy,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Latvia,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Lithuania,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Luxembourg,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Malta,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Netherlands,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Poland,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Portugal,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Romania,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Slovakia,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Slovenia,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Spain,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,Sweden,March 2022,complete,"Banned by EU Regulation 2022/350 following the invasion of Ukraine.",https://eur-lex.europa.eu/eli/reg/2022/350/oj
Russia Today,United Kingdom,March 2022,complete,"Ofcom revoked RT's broadcast license and websites were blocked by major ISPs.",https://www.theguardian.com/media/2022/mar/18/ofcom-revokes-rt-broadcast-licence-russia-today
Russia Today,Ukraine,August 2014,complete,"Banned by Ukraine along with other Russian state-owned media following the annexation of Crimea.",https://www.theguardian.com/world/2014/aug/19/ukraine-bans-russian-tv-channels"""

with open("censorship_data.csv", "r") as f:
    content = f.read()

if not content.endswith("\n"):
    content += "\n"

with open("censorship_data.csv", "w") as f:
    f.write(content + csv_entries + "\n")

from country_registry import load_registry

# The map is generated from the canonical registry. Refuse to append a new
# country until its canonical name is registered instead of silently editing a
# generated asset that the next build would overwrite.
new_countries = {
    "Australia", "Austria", "Belgium", "Bulgaria", "Canada", "Croatia",
    "Cyprus", "Czech Republic", "Denmark", "Estonia", "Finland", "France",
    "Germany", "Greece", "Hungary", "Ireland", "Italy", "Latvia",
    "Lithuania", "Luxembourg", "Malta", "Netherlands", "Poland", "Portugal",
    "Romania", "Slovakia", "Slovenia", "Spain", "Sweden", "United Kingdom",
    "Ukraine"
}
load_registry().validate_names(new_countries, "update_rt.py")
print("Done — run python3 build.py to regenerate assets/countries.js and derived files")
