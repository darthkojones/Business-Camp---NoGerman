from schemas import ClusterSchema, ClusterItemSchema

# Mock data for clusters
MOCK_CLUSTERS = [
    ClusterSchema(
        cluster_id="CL-001",
        cluster_name="O-Ring",
        item_count=3,
        common_attributes=["dimensions", "material_hardness"],
        items=[
            ClusterItemSchema(
                item_id="ITEM-101",
                raw_description="O-Ring 34,00x3,50mm 70 Shore",
                purchase_order_text="O-Ring\n34,00 x 3,50 mm\n70° Shore\nNBR",
                parsed_data={
                    "type": "O-Ring",
                    "dimensions": "34,00 x 3,50 mm",
                    "material_hardness": "70° Shore"
                }
            ),
            ClusterItemSchema(
                item_id="ITEM-102",
                raw_description="O-Ring 34,00x3,00mm 70 Shore",
                purchase_order_text="O-Ring\n34,00 x 3,00 mm\n70° Shore\nNBR",
                parsed_data={
                    "type": "O-Ring",
                    "dimensions": "34,00 x 3,00 mm",
                    "material_hardness": "70° Shore"
                }
            ),
            ClusterItemSchema(
                item_id="ITEM-103",
                raw_description="O-Ring 33,30x2,40mm Viton FPM",
                purchase_order_text="O-Ring\n33,30 x 2,40 mm\nViton FKM/FPM",
                parsed_data={
                    "type": "O-Ring",
                    "dimensions": "33,30 x 2,40 mm",
                    "material_hardness": "Viton FKM/FPM"
                }
            )
        ]
    )
]
