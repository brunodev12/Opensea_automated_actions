import os
import json
import csv
import time
import threading
from threading import Thread
from services.bidding import getBiddingMessage
from services.listing import getListingMessage
from utils.add_element_utils import save_collection_info
from utils.clear_variables import clearGlobalVariables
from utils.db_data_utils import getAllDataDB, saveAllDataDB
from utils.set_actions import setActions
from utils.concurrent_utils import getBalanceAndUserAssets
from utils.update_collections import setBlockchains, updateCollections
from data.variables import address


def run(item:dict):
    action = str(item['action'])
    if action == 'make offer':
        getBiddingMessage(item, address, balance)
    elif action == 'list token':
        getListingMessage(item, address)
    elif action == 'check offers':
        getListingMessage(item, address, True)


if __name__ == '__main__':

    updateCollections()

    collection_list = []

    with open("collection_info.json", "w") as jsonfile:
        json.dump(collection_list, jsonfile)

    for filename in os.listdir('.'):
        if filename.endswith('.csv'):
            csv_file = filename
            break

    with open(csv_file, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            collection_list.append(row)

    collection_list = sorted(
        collection_list,
        key=lambda x: (
            x['slug'],
            x['trait'] != 'yes',
            '],[' not in x['type'],
        )
    )

    setBlockchains(collection_list)

    balance, data_user_contracts, data_user_contracts_info = getBalanceAndUserAssets(address)
    if data_user_contracts is None:
        print("No user data")
        quit()

    action_list = setActions(collection_list, data_user_contracts, data_user_contracts_info)

    chunk_size = 30

    chunks = [action_list[i:i + chunk_size] for i in range(0, len(action_list), chunk_size)]

    getAllDataDB()
    
    for chunk in chunks:

        threads:list[Thread] = []
        for item in chunk:
            thread = threading.Thread(target=run, args=(item,))
            threads.append(thread)
            time.sleep(0.1)
            thread.start()

        for thread in threads:
            thread.join()
        
        clearGlobalVariables()

    save_collection_info()
    saveAllDataDB()