"""
lib/logos.py
Sector and asset class emoji helpers for NSE Market Analyst.
"""

SECTOR_EMOJI = {
    "Technology":                  "💻",
    "Financial Services":          "🏦",
    "Banking":                     "🏦",
    "Consumer Defensive":          "🛒",
    "Consumer Cyclical":           "🛍️",
    "Healthcare":                  "💊",
    "Industrials":                 "🏭",
    "Basic Materials":             "⚙️",
    "Energy":                      "⚡",
    "Real Estate":                 "🏢",
    "Communication Services":      "📡",
    "Utilities":                   "💡",
    "Automobile":                  "🚗",
    "Auto":                        "🚗",
    "Pharma":                      "💊",
    "FMCG":                        "🛒",
    "IT":                          "💻",
    "Metal":                       "⚙️",
    "Infrastructure":              "🏗️",
    "Cement":                      "🧱",
    "Telecom":                     "📱",
    "Oil & Gas":                   "🛢️",
    "Power":                       "⚡",
    "Retail":                      "🛍️",
    "Media":                       "📺",
    "Chemicals":                   "🧪",
    "Textiles":                    "🧵",
    "Agriculture":                 "🌾",
    "Unknown":                     "📊",
}


def sector_icon(sector: str) -> str:
    for key, icon in SECTOR_EMOJI.items():
        if key.lower() in sector.lower():
            return icon
    return "📊"


ASSET_EMOJI = {
    "Nifty 50":     "🔵",
    "Bank Nifty":   "🏦",
    "Sensex":       "🔴",
    "Nifty IT":     "💻",
    "Nifty Pharma": "💊",
    "Nifty Auto":   "🚗",
    "Nifty Metal":  "⚙️",
    "Nifty FMCG":   "🛒",
    "Nifty Realty": "🏢",
    "Nifty Energy": "⚡",
    "India VIX":    "📉",
    "USD/INR":      "💱",
    "Gold":         "🥇",
    "Crude Oil":    "🛢️",
}
