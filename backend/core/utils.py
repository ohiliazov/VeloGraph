def get_simple_types(categories: list[str]) -> list[str]:
    """Normalizes messy categories into strict filter types."""
    if not categories:
        return ["other"]

    results = set()
    for category_str in categories:
        cat = category_str.lower()
        if "gravel" in cat:
            results.add("gravel")
        if "mtb" in cat or "górsk" in cat:
            results.add("mtb")
        if "trekking" in cat:
            results.add("trekking")
        if "cross" in cat:
            results.add("cross")
        if "szos" in cat or "road" in cat:
            results.add("road")
        if "miejsk" in cat or "city" in cat:
            results.add("city")
        if "dzieci" in cat or "kids" in cat or "junior" in cat:
            results.add("kids")
        if "turyst" in cat:
            results.add("touring")
        if "damsk" in cat or "women" in cat:
            results.add("women")

    if not results:
        results.add("other")

    return sorted(list(results))


def get_material_group(material: str | None) -> str:
    """Groups messy material names into simplified categories."""
    if not material:
        return "other"

    mat = material.lower()
    if any(x in mat for x in ["carbon", "węgiel", "węglow"]):
        return "carbon"
    if any(x in mat for x in ["aluminum", "aluminium", "aluninium", "alu"]):
        return "aluminum"
    if any(x in mat for x in ["steel", "stal", "crmo", "chromoly"]):
        return "steel"
    if any(x in mat for x in ["titanium", "tytan"]):
        return "titanium"

    return "other"
