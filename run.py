from app import fetch_data as fd, functions as fn

# -- CONFIGURATIONS--
TRACKED_COMMODITIES = ["Gold", "Silver", "Copper"]


def main():
    to_get = []
    for commodity in TRACKED_COMMODITIES:
        if fn.verify_data_integrity(commodity) == False:
            to_get.append(commodity)
    
    if to_get:    
        fd.fetch_and_save_commodity_data(to_get)


if __name__ == "__main__":
    main()