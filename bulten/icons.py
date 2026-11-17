"""Line icons (24x24, stroke = currentColor) and the category -> icon mapping."""

_P = {
    "newspaper": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 8h10M7 12h10M7 16h6"/>',
    "building": '<path d="M3 21h18M4 10h16M12 3l8.5 7h-17z"/><path d="M6.5 10v11M10.5 10v11M13.5 10v11M17.5 10v11"/>',
    "bus": '<rect x="5" y="3" width="14" height="15" rx="3"/><path d="M5 11h14M8 18v3M16 18v3"/><circle cx="8.5" cy="14.5" r=".6"/><circle cx="15.5" cy="14.5" r=".6"/>',
    "cap": '<path d="M2 9l10-5 10 5-10 5z"/><path d="M6 11v5c0 1.5 3 3 6 3s6-1.5 6-3v-5M22 9v6"/>',
    "health": '<rect x="3" y="3" width="18" height="18" rx="5"/><path d="M12 8v8M8 12h8"/>',
    "alert": '<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18v.01"/>',
    "cloud": '<path d="M7 18h10a4 4 0 0 0 .4-8A6 6 0 0 0 6 9.6 4.3 4.3 0 0 0 7 18z"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/>',
    "book": '<path d="M2 5h6a4 4 0 0 1 4 4v11a3 3 0 0 0-3-3H2zM22 5h-6a4 4 0 0 0-4 4v11a3 3 0 0 1 3-3h7z"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "leaf": '<path d="M5 20c0-9 6-15 15-15 0 9-6 15-15 15z"/><path d="M5 20l8-8"/>',
    "trend": '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
    "factory": '<path d="M3 21V11l5 3v-3l5 3v-3l5 3V4h3v17z"/><path d="M7 17h2M12 17h2"/>',
    "sprout": '<path d="M12 21V11"/><path d="M12 11C12 7 9 5 5 5c0 4 3 6 7 6zM12 14c0-4 3-6 7-6 0 4-3 6-7 6z"/>',
    "anchor": '<circle cx="12" cy="5" r="2"/><path d="M12 7v14M8 10h8M4 14a8 8 0 0 0 16 0"/>',
    "briefcase": '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 13h18"/>',
    "store": '<path d="M4 10v10h16V10M3 10l2-6h14l2 6z"/><path d="M9 20v-6h6v6"/>',
    "ball": '<circle cx="12" cy="12" r="9"/><path d="M12 7.5l4 2.9-1.5 4.6h-5L8 10.4z"/><path d="M12 3v4.5M21 10.5l-5 0M17.5 19.5l-3-4.5M6.5 19.5l3-4.5M3 10.5h5"/>',
    "megaphone": '<path d="M3 10v4h3l7 5V5l-7 5z"/><path d="M17 9a4 4 0 0 1 0 6M19.5 6.5a7.5 7.5 0 0 1 0 11"/>',
    "bolt": '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
    "droplet": '<path d="M12 3s7 7.5 7 12a7 7 0 0 1-14 0c0-4.5 7-12 7-12z"/>',
    "pharmacy": '<path d="M10 3h4v7h7v4h-7v7h-4v-7H3v-4h7z"/>',
    "pin": '<path d="M12 21s-7-7.4-7-12a7 7 0 0 1 14 0c0 4.6-7 12-7 12z"/><circle cx="12" cy="9" r="2.5"/>',
    "sunrise": '<path d="M12 3v5M9 6l3-3 3 3M4.5 12.5l1.5 1.5M19.5 12.5L18 14M2 19h20M7 19a5 5 0 0 1 10 0"/>',
    "sunset": '<path d="M12 8V3M9 5l3 3 3-3M4.5 12.5l1.5 1.5M19.5 12.5L18 14M2 19h20M7 19a5 5 0 0 1 10 0"/>',
    "waves": '<path d="M2 8c2 0 2-2 4-2s2 2 4 2 2-2 4-2 2 2 4 2 2-2 4-2M2 13c2 0 2-2 4-2s2 2 4 2 2-2 4-2 2 2 4 2 2-2 4-2M2 18c2 0 2-2 4-2s2 2 4 2 2-2 4-2 2 2 4 2 2-2 4-2"/>',
    "bookmark": '<path d="M6 3h12v18l-6-4.5L6 21z"/>',
    "send": '<path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4z"/>',
    "follow": '<circle cx="9" cy="8" r="4"/><path d="M2 21a7 7 0 0 1 14 0M19 8v6M16 11h6"/>',
    "bulb": '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-4 10.5c.8.8 1 1.5 1 2.5h6c0-1 .2-1.7 1-2.5A6 6 0 0 0 12 3z"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "wind": '<path d="M3 8h11a3 3 0 1 0-3-3M3 12h16a3 3 0 1 1-3 3M3 16h7"/>',
    "umbrella": '<path d="M12 3a9 9 0 0 1 9 9H3a9 9 0 0 1 9-9zM12 12v7a2 2 0 0 0 4 0"/>',
    "sun": '<circle cx="12" cy="12" r="4.5"/><path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8"/>',
    "rain": '<path d="M7 15h10a4 4 0 0 0 .4-8A6 6 0 0 0 6 6.6 4.3 4.3 0 0 0 7 15z"/><path d="M8 18l-1 3M12 18l-1 3M16 18l-1 3"/>',
    "snow": '<path d="M7 15h10a4 4 0 0 0 .4-8A6 6 0 0 0 6 6.6 4.3 4.3 0 0 0 7 15z"/><path d="M8 19v.01M12 21v.01M16 19v.01" stroke-width="3"/>',
    "fog": '<path d="M4 9h16M2 13h20M5 17h14"/>',
    "storm": '<path d="M7 15h10a4 4 0 0 0 .4-8A6 6 0 0 0 6 6.6 4.3 4.3 0 0 0 7 15z"/><path d="M12 15l-2.5 4h4L11 23"/>',
    "arrow": '<path d="M4 12h16M14 6l6 6-6 6"/>',
}

# Category names the writer may use (fixed list) -> icon.
CATEGORY_ICONS = {
    "Gündem": "newspaper", "Belediye": "building", "Yönetim": "building", "Ulaşım": "bus", "Eğitim": "cap",
    "Sağlık": "health", "Afet": "alert", "Hava": "cloud", "Asayiş": "shield", "Kültür": "book",
    "Etkinlik": "calendar", "Çevre": "leaf", "Ekonomi": "trend", "Sanayi": "factory", "Tarım": "sprout",
    "Liman": "anchor", "İstihdam": "briefcase", "Ticaret": "store", "Enerji": "bolt", "Altyapı": "droplet",
    "Duyuru": "megaphone", "Futbol": "ball", "Basketbol": "ball", "Voleybol": "ball", "Spor": "ball",
    "Samsunspor": "ball",
}
CATEGORIES = list(CATEGORY_ICONS)


def svg(name: str, stroke: float = 1.8, cls: str = "") -> str:
    body = _P.get(name, _P["newspaper"])
    c = f' class="{cls}"' if cls else ""
    return (f'<svg{c} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="{stroke}" '
            f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>')


def for_category(category: str) -> str:
    return CATEGORY_ICONS.get(category, "newspaper")
