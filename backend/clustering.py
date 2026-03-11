import re
from typing import List, Dict, Any
from collections import defaultdict
from sqlalchemy.orm import Session
from schemas import ClusterSchema, ClusterItemSchema
from models import Material
from mock_data import MOCK_CLUSTERS

def parse_material_data(family: str, text: str) -> Dict[str, Any]:
    parsed = {"type": family}
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    if family == "O-Ring":
        # e.g., "34,00 x 3,50 mm", "70° Shore", "Viton FKM/FPM"
        for line in lines[1:]: # skip first line which is usually "O-Ring"
            if 'x' in line and ('mm' in line.lower() or ',' in line):
                parsed["dimensions"] = line
            elif 'Shore' in line:
                parsed["material_hardness"] = line
            elif 'NBR' in line or 'Viton' in line or 'EPDM' in line or 'FPM' in line:
                parsed["material"] = line

    elif family == "Wellendichtring":
        for line in lines[1:]:
            if 'x' in line:
                parsed["dimensions"] = line
            else:
                parsed["type_detail"] = line # e.g. BASL, B1SL

    elif family == "Schraube" or family == "Mutter":
        for line in lines[1:]:
            if line.startswith('M') or 'x' in line:
                parsed["dimensions"] = line
            elif 'DIN' in line:
                parsed["norm"] = line
            elif 'verz' in line or 'schw' in line or 'Edelstahl' in line:
                parsed["material_treatment"] = line
                
    elif family == "Servomotor":
        # Extract Key Value pairs, e.g. "Hersteller       BAELZ"
        for line in lines[1:]:
            # match "Key    Value" or "Key: Value"
            parts = re.split(r'\s{2,}|\s*:\s*', line, maxsplit=1)
            if len(parts) == 2:
                key, val = parts
                safe_key = key.strip().lower().replace(' ', '_').replace('[kw]', 'kw')
                parsed[safe_key] = val.strip()

    elif family == "Kettenrad":
        for line in lines[1:]:
            if 'Z' in line and '=' in line: # e.g. Z = 16
                parsed["teeth"] = line
            elif 'Z' in line and any(c.isdigit() for c in line): # e.g. Z16
                match = re.search(r'Z\s*(\d+)', line)
                if match:
                    parsed["teeth"] = match.group(1)
            if '"' in line:
                parsed["inches"] = line.strip()

    else:
        # Generic fallback
        if len(lines) > 1:
            parsed["details"] = " | ".join(lines[1:])
            
    return parsed

def get_product_family(text: str) -> str:
    if not text:
        return "Unknown"
        
    first_line = text.strip().split('\n')[0].strip()
    # Normalize family name
    first_word = first_line.split(' ')[0].split('-')[0] if '-' not in first_line else first_line.split(' ')[0]
    
    known_families = ["O-Ring", "Wellendichtring", "Mutter", "Schraube", "Servomotor", "Kettenrad", "PN-Zylinder", "Lager", "GT-Motor"]
    
    for family in known_families:
        if text.lower().startswith(family.lower()):
            return family
            
    # Try to return the first word if it looks like a noun (starts with capital)
    if first_word and first_word.istitle():
        return first_word
        
    return "Others"

def generate_clusters(db: Session = None) -> List[ClusterSchema]:
    """
    Generates product clusters based on shared properties.
    If DB is provided, it extracts the real data. Otherwise it returns mock data.
    """
    if db is None:
        return MOCK_CLUSTERS
        
    materials = db.query(Material).all()
    
    # We will build clusters: Family -> List[ClusterItemSchema]
    clusters_dict = defaultdict(list)
    
    for mat in materials:
        text = mat.purchase_order_text or mat.short_text or ""
        family = get_product_family(text)
        
        parsed_data = parse_material_data(family, text)
        
        item = ClusterItemSchema(
            item_id=mat.material_number,
            raw_description=text.replace('\n', ' ')[:100],  # Shorten for display
            parsed_data=parsed_data
        )
        clusters_dict[family].append(item)
        
    # Now convert to the output schema
    result_clusters = []
    cluster_idx = 1
    
    for family, items in clusters_dict.items():
        # Find common attributes among ALL items in this cluster
        if not items:
            continue
            
        common_attrs = set(items[0].parsed_data.keys())
        for item in items[1:]:
            common_attrs.intersection_update(item.parsed_data.keys())
            
        cluster_id = f"CL-{cluster_idx:03d}"
        cluster_idx += 1
        
        result_clusters.append(
            ClusterSchema(
                cluster_id=cluster_id,
                cluster_name=family,
                item_count=len(items),
                common_attributes=list(common_attrs),
                items=items
            )
        )
        
    # Sort clusters by size descending
    result_clusters.sort(key=lambda c: c.item_count, reverse=True)
    
    return result_clusters
