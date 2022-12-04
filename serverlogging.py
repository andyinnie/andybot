# serverlogging.py
from datetime import timedelta

import discord

import util

LOGGING_CHANNEL_ID = 942838963155136543
LOGGING2_CHANNEL_ID = 942838979961704518
LOGGING_CACHE_COOLDOWN = timedelta(seconds=1)


def load(core):
    # ============================== #
    # ========== ON  EDIT ========== #
    # ============================== #

    @core.bot.event
    async def on_message_edit(before, after):
        logging_channel = await core.channel_provider(LOGGING_CHANNEL_ID)
        author = after.author

        if author.id == core.bot.user.id:
            return

        if before.content == after.content:
            return

        embed = discord.Embed(
            title=f'Message edited in #{after.channel.name}',
            color=util.Color.andyinnie,
            timestamp=util.now_dt()
        ).set_author(
            name=f'{author.name}#{author.discriminator}',
            icon_url=author.avatar.url
        ).add_field(
            name='Before',
            value=util.shorten(before.content, 1024) if before.content else "*empty message*",
            inline=False
        ).add_field(
            name='After',
            value=util.shorten(after.content, 1024) if after.content else "*empty message*",
            inline=False
        )

        await logging_channel.send(embed=embed)

    @core.bot.event
    async def on_raw_message_edit(payload):
        # cached messages cause both edit events to be fired.
        # so, catch cached messages here
        if payload.cached_message:
            return

        channel = core.bot.get_channel(payload.channel_id)
        new_message = await channel.fetch_message(payload.message_id)
        core.bot.dispatch('message_edit',
                          util.FakeMessage(content='*Message not cached*',
                                           author=new_message.author,
                                           channel=new_message.channel),
                          new_message)

    # ============================== #
    # ========= ON  DELETE ========= #
    # ============================== #

    @core.bot.event
    async def on_message_delete(message):
        logging_channel = await core.channel_provider(LOGGING_CHANNEL_ID)

        author = message.author

        if author.bot:
            return

        if not hasattr(message.channel, 'name'):
            return

        embed = discord.Embed(
            title=f'Message deleted in #{message.channel.name}',
            description=util.shorten(message.content, 1024) if message.content else "*empty message*",
            color=util.Color.red,
            timestamp=util.now_dt()
        ).set_author(
            name=f'{author.name}#{author.discriminator}',
            icon_url=author.avatar.url
        )

        await logging_channel.send(embed=embed)

        if attachments := message.attachments:
            await logging_channel.send(
                embed=discord.Embed(
                    title=f'That message had the following attachment{"" if len(attachments) == 1 else "s"}:',
                    description='\n'.join([a.url for a in attachments]),
                    color=util.Color.red,
                    timestamp=util.now_dt()
                )
            )

    @core.bot.event
    async def on_raw_message_delete(payload):
        # cached messages cause both delete events to be fired.
        # so, catch cached messages here
        if payload.cached_message:
            return

        logging_channel = await core.channel_provider(LOGGING_CHANNEL_ID)

        embed = discord.Embed(
            title=f'Uncached message deleted in #{core.bot.get_channel(payload.channel_id).name}',
            description=f'Message ID: {payload.message_id}',
            color=util.Color.red,
            timestamp=util.now_dt()
        )

        await logging_channel.send(embed=embed)

    # ============================== #
    # ======= MEMBER  UPDATE ======= #
    # ============================== #

    update_cache = dict()

    @core.bot.event
    async def on_member_update(before, after):
        core.bot.dispatch('user_update', before, after)

    @core.bot.event
    async def on_user_update(before, after):
        # reject duplicate updates (this event fires once for each server a member is in with the bot)
        nonlocal update_cache
        rn = util.now_dt()
        if before.id in update_cache.keys():
            if rn - update_cache[before.id] < LOGGING_CACHE_COOLDOWN:
                return
        update_cache[before.id] = rn

        logging_2_channel = await core.channel_provider(LOGGING2_CHANNEL_ID)

        async def internal(before_val, after_val, name):
            if before_val != after_val:
                await logging_2_channel.send(
                    embed=discord.Embed(
                        title=f'{name} change',
                        color=util.Color.good_random(seed=before.id),
                        timestamp=util.now_dt()
                    ).set_author(
                        name=f'{before.name}#{before.discriminator}',
                        icon_url=before.avatar.url
                    ).add_field(
                        name='Before',
                        value=before_val,
                    ).add_field(
                        name='After',
                        value=after_val,
                    )
                )

        if isinstance(before, discord.Member):
            # await internal(before.status, after.status, 'status')
            await internal(before.nick, after.nick, 'nickname')
        else:
            await internal(before.avatar.url, after.avatar.url, 'avatar')
            await internal(before.name, after.name, 'username')
            await internal(before.discriminator, after.discriminator, 'discriminator')

    print('Registered server logging events')
