from services.detector import detect
from services.dispatcher import dispatch

async def process_message(message):
    result = detect(message.content)

    if result is None:
        return 

    print(result)

    await dispatch(message, result)