import csv

new_data = [
    ["Discord", "Islamic Republic of Iran", "Unknown", "complete", "Blocked by government firewalls, particularly affecting voice and video calls.", "https://www.iranhumanrights.org/"],
    ["DuckDuckGo", "Islamic Republic of Iran", "Unknown", "complete", "Access is frequently restricted or blocked due to Islamic Republic of Iran's systemic censorship infrastructure.", "https://ooni.org/"],
    ["Google", "Islamic Republic of Iran", "Longstanding", "partial", "Intermittent blocking of services like Search and Play Store; also restricted by US sanctions.", "https://www.aljazeera.com/"],
    ["LINE", "Islamic Republic of Iran", "January 2015", "complete", "Blocked by the Iranian judiciary alongside other messaging apps.", "https://www.ctvnews.ca/"],
    ["LinkedIn", "Islamic Republic of Iran", "Longstanding", "partial", "Restricted access due to US sanctions, resulting in account limitations for users in Islamic Republic of Iran, alongside government censorship.", "https://paaia.org/"],
    ["Medium", "Islamic Republic of Iran", "Unknown", "complete", "Blocked as part of Islamic Republic of Iran's broader filtering infrastructure targeting foreign publishing platforms.", "https://freedomhouse.org/"],
    ["Netflix", "Islamic Republic of Iran", "2016", "complete", "Netflix is unavailable in Islamic Republic of Iran due to US sanctions, and the service is also blocked by Iranian authorities.", "https://iranhumanrights.org/"],
    ["Odnoklassniki", "Islamic Republic of Iran", "Unknown", "complete", "Subject to the same systemic blocking and filtering infrastructure that restricts access to most international social networking sites.", "https://ooni.org/"],
    ["Quora", "Islamic Republic of Iran", "Unknown", "complete", "Effectively blocked and inaccessible without the use of circumvention tools.", "https://freedomhouse.org/"],
    ["Reddit", "Islamic Republic of Iran", "Unknown", "complete", "Filtered and inaccessible without the use of Virtual Private Networks (VPNs).", "https://freedomhouse.org/"],
    ["Roblox", "Islamic Republic of Iran", "Unknown", "complete", "Inaccessible without a VPN due to filtering, and lacks official support for Iranian phone numbers.", "https://freedomhouse.org/"],
    ["Rumble", "Islamic Republic of Iran", "Unknown", "complete", "Blocked as part of the Iranian government's broad internet filtering system.", "https://cigionline.org/"],
    ["Spotify", "Islamic Republic of Iran", "Longstanding", "complete", "Unavailable due to a combination of Spotify's compliance with US sanctions and local internet censorship.", "https://surfiran.com/"],
    ["TikTok", "Islamic Republic of Iran", "Unknown", "complete", "Blocked by the Committee for Determining Instances of Criminal Content at the network level.", "https://surfiran.com/"],
    ["Twitch", "Islamic Republic of Iran", "Unknown", "complete", "Blocked or heavily restricted as part of the country's extensive internet censorship system.", "https://netblocks.org/"],
    ["VKontakte", "Islamic Republic of Iran", "Unknown", "complete", "Blocked by broad, systematic blocking of major foreign social media platforms.", "https://ooni.org/"],
    ["Vimeo", "Islamic Republic of Iran", "Unknown", "complete", "Restricted due to the Iranian government's extensive internet filtering.", "https://ooni.org/"],
    ["WeChat", "Islamic Republic of Iran", "2013", "partial", "Blocked in September 2013 due to privacy and content concerns, though reportedly unblocked in 2018, access remains inconsistent.", "https://netblocks.org/"],
    ["Wikipedia", "Islamic Republic of Iran", "Longstanding", "partial", "Subject to targeted blocks, intermittent disruptions, and DNS tampering, particularly affecting the Farsi edition.", "https://ooni.org/"],
    ["Yandex", "Islamic Republic of Iran", "Longstanding", "partial", "Subject to broad censorship and internet disruptions, though not explicitly targeted like Western platforms.", "https://netblocks.org/"]
]

rows = []
with open("censorship_data.csv", "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    header = next(reader)
    for row in reader:
        rows.append(row)

rows.extend(new_data)
# Sort by platform
rows.sort(key=lambda x: (x[0].lower(), x[1].lower()))

with open("censorship_data.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(rows)

print("Added new entries and sorted the file.")
