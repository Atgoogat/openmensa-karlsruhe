def getOpenMensaMetaData(canteen: str):
    try:
        with open('./meta/' + canteen + '.xml') as data:
            return data.read()
    except:
        return None
