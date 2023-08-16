import json

hooks = dict()


def build_json_handler(handler):
    return lambda message: handler(json.loads(message.content))


def load(core):
    def register_hook_json(listen_id, handler):
        current_hooks = core.exports.get('webhook/hooks')
        current_hooks()[listen_id] = build_json_handler(handler)

    core.exports.put('webhook/hooks', hooks)
    core.exports.put('webhook/register', register_hook_json)

    async def handle_reqpy(payload):
        # channel_id = payload['channel_id']
        channel_id = 942838758074638439
        message = payload['message']
        channel = core.bot.get_channel(channel_id)
        await channel.send(message)
    register_hook_json(1100620506434113568, handle_reqpy)
