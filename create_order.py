import json
import time
import threading
from src.cancel_order_src import cancelOrderSrc
from src.create_offer import createOffer
from src.create_single_offer import createSingleOffer
from src.create_listing_order import createListingOrder
from decimal import Decimal
from data.constants import chainId_dict, chain_dict, types_cancelOffer, symbols
from utils.db_data_utils import saveCompetitiveData
from utils.sign_str_message import signTypedMessage
from database.connection import closeConnection
from data.variables import lock

def createOrder(j:dict):
    try:
        bought:bool = j['bought']
    except KeyError:
        return
    
    order_hash = j.get('order_hash')
    if order_hash:
        time_now = int(time.time())
        j['timestamp'] = time_now
        j['itemType'] = [2, 4] if j['token standard'] == 'ERC-721' else [3, 5]
        return
    
    _id = str(j['ID'])


    if j['typed_message']:
        startTime = int(j['typed_message']['message']['startTime'])
        endTime = int(j['typed_message']['message']['endTime'])
        order_duration = endTime - startTime
        new_startTime = int(time.time())
        j['typed_message']['message']['startTime'] = str(new_startTime)
        j['typed_message']['message']['endTime'] = str(new_startTime + order_duration)
    
    if bought==True:
        if j['typed_message'] is not None:
            signature = signTypedMessage(j['typed_message'])
            parameters = j['typed_message']['message']
            chainId = j['typed_message']['domain']['chainId']
            chain = chainId_dict[chainId]
            listing_response = {}
            with lock:
                listing_response = createListingOrder(parameters, signature, chain, _id)
            if listing_response:
                order_hash = listing_response['order']['order_hash']
                protocol_address = listing_response['order']['protocol_address']
                currency = listing_response['order']['taker_asset_bundle']['assets'][0]['asset_contract']['symbol']
                if currency in symbols:
                    listing_value_wei = listing_response['order']['current_price']
                    decimals = listing_response['order']['taker_asset_bundle']['assets'][0]['decimals']
                    listing_value_eth = float(Decimal(listing_value_wei)/Decimal(f"{10**decimals}"))
                    j['my_price'] = listing_value_eth
                j['order_hash'] = order_hash
                j['chain'] = chain
                j['protocol_address'] = protocol_address
                time_now = int(time.time())
                j['order_timestamp'] = time_now
                j['timestamp'] = time_now
                j['itemType'] = [2, 4] if j['token standard'] == 'ERC-721' else [3, 5]
    else:
        if j['typed_message'] is not None:
            slug = str(j['slug'])
            trait:bool = j['trait']=="yes"
            _type = None if (j['type'] == '' or not trait) else j['type']
            _value = None if (j['type'] == '' or not trait) else j['value']
            signature = signTypedMessage(j['typed_message'])
            parameters = j['typed_message']['message']
            if j['assets'] == '' or trait:
                collectionOffer_response = {}
                with lock:
                    collectionOffer_response = createOffer(slug, _type, _value, parameters, signature, _id)
                if collectionOffer_response:
                    order_hash = collectionOffer_response['order_hash']
                    chain = collectionOffer_response['chain']
                    price = collectionOffer_response['price']
                    criteria = collectionOffer_response['criteria']
                    currency = price['currency']
                    protocol_address = collectionOffer_response['protocol_address']
                    if currency in symbols:
                        offer_value_wei = price['value']
                        decimals = price['decimals']
                        offer_value_eth = float(Decimal(offer_value_wei)/Decimal(f"{10**decimals}"))
                        j['my_price'] = offer_value_eth
                    j['order_hash'] = order_hash
                    j['chain'] = chain
                    j['protocol_address'] = protocol_address
                    j['criteria'] = criteria
                    time_now = int(time.time())
                    j['order_timestamp'] = time_now
                    j['timestamp'] = time_now
                    j['itemType'] = [2, 4] if j['token standard'] == 'ERC-721' else [3, 5]
                    j['normal_offer'] = True

            else:
                chainId = j['typed_message']['domain']['chainId']
                chain = chainId_dict[chainId]
                singleOffer_response = {}
                with lock:
                    singleOffer_response = createSingleOffer(parameters, signature, chain, _id)
                if singleOffer_response:
                    order_hash = singleOffer_response['order']['order_hash']
                    currency = singleOffer_response['order']['maker_asset_bundle']['assets'][0]['asset_contract']['symbol']
                    protocol_address = singleOffer_response['order']['protocol_address']
                    if currency in symbols:
                        offer_value_wei = singleOffer_response['order']['current_price']
                        decimals = singleOffer_response['order']['maker_asset_bundle']['assets'][0]['decimals']
                        offer_value_eth = float(Decimal(offer_value_wei)/Decimal(f"{10**decimals}"))
                        j['my_price'] = offer_value_eth
                    j['order_hash'] = order_hash
                    j['chain'] = chain
                    j['protocol_address'] = protocol_address
                    time_now = int(time.time())
                    j['order_timestamp'] = time_now
                    j['timestamp'] = time_now
                    j['itemType'] = [2, 4] if j['token standard'] == 'ERC-721' else [3, 5]
                    j['normal_offer'] = True

def cancelOrder(i:list[str]):

    order_hash = i[0]
    chain = i[1]
    protocol_address = i[2]

    domain = {
        "name": "Seaport",
        "version": "1.6",
        "chainId": chain_dict[chain],
        "verifyingContract": protocol_address
    }

    typed_message_cancel_order:dict = {
        "types": types_cancelOffer,
        "primaryType": 'OrderHash',
        "domain": domain,
        "message": {"orderHash": order_hash}
    }

    signature = signTypedMessage(typed_message_cancel_order)
    with lock:
        cancelOrderSrc(chain, protocol_address, order_hash, signature)

    
if __name__ == '__main__':

    with open("collection_info.json") as jsonfile:
        collection_info:list[dict] = json.load(jsonfile)

    threads = []
    for item in collection_info:
        thread = threading.Thread(target=createOrder, args=(item,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    with open("offers_to_cancel.json") as jsonfile:
        offers_to_cancel:list[list] = json.load(jsonfile)

    threads = []
    for item in offers_to_cancel:
        thread = threading.Thread(target=cancelOrder, args=(item,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()

    saveCompetitiveData(collection_info)
    closeConnection()
