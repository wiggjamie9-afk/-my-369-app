"""The starter parts library: 50 common HVAC install items.

EVERY PRICE HERE IS A PLACEHOLDER. They are round-number stand-ins so the app
can be exercised on day one; none came from a supplier price list and none
came from any other product. Each row is stored with price_status
"placeholder", the app marks such lines "check price", and the review step
will not send a quote until a person has confirmed them. Replace them by
importing your supplier list (Parts > Import CSV).

Columns: sku, name, category, brand, vendor, unit, list cost in dollars, kW (or None)
"""

SEED_PARTS = [
    # wall split systems (indoor + outdoor package)
    ("SPL-DAI-25", "Daikin 2.5kW wall split system (package)", "unit-split", "Daikin", "Main supplier", "ea", "900.00", "2.5"),
    ("SPL-DAI-35", "Daikin 3.5kW wall split system (package)", "unit-split", "Daikin", "Main supplier", "ea", "1100.00", "3.5"),
    ("SPL-DAI-50", "Daikin 5.0kW wall split system (package)", "unit-split", "Daikin", "Main supplier", "ea", "1500.00", "5.0"),
    ("SPL-DAI-71", "Daikin 7.1kW wall split system (package)", "unit-split", "Daikin", "Main supplier", "ea", "2000.00", "7.1"),
    ("SPL-MEL-25", "Mitsubishi Electric 2.5kW wall split system (package)", "unit-split", "Mitsubishi Electric", "Main supplier", "ea", "950.00", "2.5"),
    ("SPL-MEL-35", "Mitsubishi Electric 3.5kW wall split system (package)", "unit-split", "Mitsubishi Electric", "Main supplier", "ea", "1150.00", "3.5"),
    ("SPL-MEL-50", "Mitsubishi Electric 5.0kW wall split system (package)", "unit-split", "Mitsubishi Electric", "Main supplier", "ea", "1550.00", "5.0"),
    ("SPL-MEL-71", "Mitsubishi Electric 7.1kW wall split system (package)", "unit-split", "Mitsubishi Electric", "Main supplier", "ea", "2050.00", "7.1"),
    ("SPL-FUJ-25", "Fujitsu 2.5kW wall split system (package)", "unit-split", "Fujitsu", "Main supplier", "ea", "850.00", "2.5"),
    ("SPL-FUJ-35", "Fujitsu 3.5kW wall split system (package)", "unit-split", "Fujitsu", "Main supplier", "ea", "1050.00", "3.5"),
    ("SPL-FUJ-50", "Fujitsu 5.0kW wall split system (package)", "unit-split", "Fujitsu", "Main supplier", "ea", "1450.00", "5.0"),
    ("SPL-FUJ-71", "Fujitsu 7.1kW wall split system (package)", "unit-split", "Fujitsu", "Main supplier", "ea", "1950.00", "7.1"),
    # multi split
    ("MUL-DAI-OUT-80", "Daikin 8.0kW multi-split outdoor unit", "unit-multi-outdoor", "Daikin", "Main supplier", "ea", "2400.00", "8.0"),
    ("MUL-DAI-IN-25", "Daikin 2.5kW multi-split indoor wall unit", "unit-multi-indoor", "Daikin", "Main supplier", "ea", "600.00", "2.5"),
    ("MUL-DAI-IN-35", "Daikin 3.5kW multi-split indoor wall unit", "unit-multi-indoor", "Daikin", "Main supplier", "ea", "700.00", "3.5"),
    ("MUL-MEL-OUT-80", "Mitsubishi Electric 8.0kW multi-split outdoor unit", "unit-multi-outdoor", "Mitsubishi Electric", "Main supplier", "ea", "2500.00", "8.0"),
    ("MUL-MEL-IN-25", "Mitsubishi Electric 2.5kW multi-split indoor wall unit", "unit-multi-indoor", "Mitsubishi Electric", "Main supplier", "ea", "650.00", "2.5"),
    ("MUL-MEL-IN-35", "Mitsubishi Electric 3.5kW multi-split indoor wall unit", "unit-multi-indoor", "Mitsubishi Electric", "Main supplier", "ea", "750.00", "3.5"),
    # ducted
    ("DUC-DAI-71", "Daikin 7.1kW ducted system (package)", "unit-ducted", "Daikin", "Main supplier", "ea", "3000.00", "7.1"),
    ("DUC-DAI-100", "Daikin 10.0kW ducted system (package)", "unit-ducted", "Daikin", "Main supplier", "ea", "3800.00", "10.0"),
    ("DUC-DAI-125", "Daikin 12.5kW ducted system (package)", "unit-ducted", "Daikin", "Main supplier", "ea", "4500.00", "12.5"),
    ("DUC-DAI-140", "Daikin 14.0kW ducted system (package)", "unit-ducted", "Daikin", "Main supplier", "ea", "5200.00", "14.0"),
    # refrigeration pipe
    ("PIPE-PAIR-6-10", "Pair coil 1/4 + 3/8 insulated copper", "pipe", "", "Main supplier", "m", "12.00", None),
    ("PIPE-PAIR-6-12", "Pair coil 1/4 + 1/2 insulated copper", "pipe", "", "Main supplier", "m", "15.00", None),
    ("PIPE-PAIR-10-16", "Pair coil 3/8 + 5/8 insulated copper", "pipe", "", "Main supplier", "m", "22.00", None),
    # electrical
    ("ELEC-CB-20", "20A circuit breaker", "electrical", "", "Electrical wholesaler", "ea", "18.00", None),
    ("ELEC-ISO-20", "20A weatherproof isolator switch", "electrical", "", "Electrical wholesaler", "ea", "25.00", None),
    ("ELEC-TPS-25", "2.5mm2 twin and earth power cable", "electrical", "", "Electrical wholesaler", "m", "3.00", None),
    ("ELEC-INTER-15", "1.5mm2 4-core interconnect cable", "electrical", "", "Electrical wholesaler", "m", "3.50", None),
    # mounting
    ("MNT-SLAB", "Polymer outdoor unit slab", "mounting", "", "Main supplier", "ea", "45.00", None),
    ("MNT-BRKT", "Outdoor unit wall bracket (pair)", "mounting", "", "Main supplier", "ea", "60.00", None),
    ("MNT-FEET", "Rubber mounting feet (set of 2)", "mounting", "", "Main supplier", "ea", "30.00", None),
    ("MNT-ROOF", "Roof mount bracket kit", "mounting", "", "Main supplier", "ea", "120.00", None),
    # drainage
    ("DRN-PVC-20", "20mm PVC condensate drain", "drainage", "", "Main supplier", "m", "4.00", None),
    ("DRN-PUMP", "Condensate pump", "drainage", "", "Main supplier", "ea", "140.00", None),
    # trunking
    ("TRK-80-2M", "80mm line-set trunking, 2m length", "trunking", "", "Main supplier", "ea", "28.00", None),
    ("TRK-80-ELB", "80mm trunking elbow", "trunking", "", "Main supplier", "ea", "12.00", None),
    # ducting
    ("DCT-FLEX-250", "250mm insulated flexible duct, 6m", "ducting", "", "Main supplier", "ea", "70.00", None),
    ("DCT-FLEX-300", "300mm insulated flexible duct, 6m", "ducting", "", "Main supplier", "ea", "85.00", None),
    ("DCT-PLENUM", "Supply air plenum box", "ducting", "", "Main supplier", "ea", "220.00", None),
    ("DCT-DIFF", "Ceiling diffuser outlet with neck", "ducting", "", "Main supplier", "ea", "45.00", None),
    ("DCT-RAG", "Return air grille with filter", "ducting", "", "Main supplier", "ea", "160.00", None),
    ("DCT-DAMPER", "Motorised zone damper", "ducting", "", "Main supplier", "ea", "150.00", None),
    # controls
    ("CTL-WALL", "Wired wall controller", "controls", "", "Main supplier", "ea", "180.00", None),
    ("CTL-WIFI", "Wi-Fi control adapter", "controls", "", "Main supplier", "ea", "130.00", None),
    ("CTL-ZONE", "Zone controller (up to 8 zones)", "controls", "", "Main supplier", "ea", "420.00", None),
    # consumables and service
    ("CON-R32", "R32 refrigerant top-up", "consumables", "", "Main supplier", "kg", "40.00", None),
    ("CON-SUNDRY", "Fixings, sealant and sundries", "consumables", "", "Main supplier", "ea", "35.00", None),
    ("SVC-CALLOUT", "Service call-out", "service", "", "", "ea", "40.00", None),
    ("SVC-KIT", "Service consumables per unit (coil cleaner, filter wash)", "service", "", "", "ea", "15.00", None),
]

SEED_VENDORS = [("Main supplier", 0), ("Electrical wholesaler", 0)]
