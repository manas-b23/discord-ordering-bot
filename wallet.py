import json
import os
import discord
import asyncio
import datetime
from discord import app_commands
from extras import Utils, Checkers


class Actions:
    def make_wallet(self, user_id):
        # Gets the user's wallet
        filepath = os.path.dirname(os.path.abspath(
            __file__)) + f"/data/wallets/{str(user_id)}.json"
        # Makes it fit your OS
        filepath = Utils.path_finder(filepath)
        # Makes the wallet if it doesn't exist
        if not os.path.isfile(filepath):
            user_file = {
                "user_id": str(user_id),
                "balance": 0,
                "email": "",
            }
            # Saves the wallet
            json.dump(user_file, open(filepath, "w"), indent=4)
        return filepath

    def add_email(self, user_id, email):
        wallet = self.get_wallet(user_id)
        wallet["data"]["email"] = email
        json.dump(wallet["data"], open(wallet["filepath"], "w"), indent=4)

    def get_email(self, user_id):
        wallet = self.get_wallet(user_id)["data"]["email"]
        if wallet == "":
            return None
        return wallet

    def get_wallet(self, user_id):
        # Gets the user's wallet from the make_wallet function
        filepath = self.make_wallet(user_id)
        # Loads the wallet
        user_data = json.load(open(filepath, 'r'))
        # Returns the wallet
        return {"data": user_data, "filepath": filepath}

    def add_balance(self, user_id, amount):
        # gets the wallet
        wallet = self.get_wallet(user_id)
        # Adds the amount to the balance
        wallet["data"]["balance"] += amount  # adds the amount to the balance
        wallet["data"]["balance"] = round(wallet["data"]["balance"], 2)
        # Saves it in the users data
        json.dump(wallet["data"], open(wallet["filepath"], "w"), indent=4)

    def remove_balance(self, user_id, amount):
        class TooMuchSpent(Exception):
            pass
        # gets the wallet
        wallet = self.get_wallet(user_id)
        # Spends the amount from the balance
        wallet["data"]["balance"] -= amount
        wallet["data"]["balance"] = round(wallet["data"]["balance"], 2)
        # Error if the balance is less than 0
        if wallet["data"]["balance"] < 0:
            raise TooMuchSpent("I see shenanigans")
        # Saves it in the users data, if the balance is greater than 0
        json.dump(wallet["data"], open(wallet["filepath"], "w"), indent=4)

    def get_transactions(self, user_id):
        # Gets the user's transactions
        filepath = os.path.dirname(os.path.abspath(
            __file__)) + f"/data/transactions/{str(user_id)}.json"
        # Makes it fit your OS
        filepath = Utils.path_finder(filepath)
        # Makes the transactions if it doesn't exist
        if not os.path.isfile(filepath):
            user_file = {
                "user_id": str(user_id),
                "orders": {},
                "reloads": {},
            }
            # Saves the transactions
            json.dump(user_file, open(filepath, "w"), indent=4)
        # Loads the transactions
        user_data = json.load(open(filepath, 'r'))
        # Returns the transactions
        return {"data": user_data, "filepath": filepath}

    def add_order(self, user_id, order_id, amount, cart, status, instructions: None):
        # Gets the user's transactions
        transactions = self.get_transactions(user_id)
        # Adds the order to the transactions
        transactions["data"]["orders"][order_id] = {
            "amount": amount,
            "status": status,
            "cart": cart,
        }
        # Adds the instructions if there are any
        if instructions is not None:
            transactions["data"]["orders"][order_id]["instructions"] = instructions
        # Saves the transactions
        json.dump(transactions["data"], open(
            transactions["filepath"], "w"), indent=4)

    def add_reload(self, user_id, reload_id, amount, status, invoice=None):
        # Gets the user's transactions
        transactions = self.get_transactions(user_id)
        # Adds the reload to the transactions
        transactions["data"]["reloads"][reload_id] = {
            "amount": amount,
            "status": status,
            "invoice": invoice,
        }
        # Saves the transactions
        json.dump(transactions["data"], open(
            transactions["filepath"], "w"), indent=4)


class WalletActions(app_commands.Group):

    action_object = Actions()

    def __init__(self, bot: discord.Client):
        super().__init__(name="wallet", description="Perform actions on your wallet")
        self.bot = bot

    @app_commands.command(name="view", description="View your wallet")
    async def view_wallet(self, interaction: discord.Interaction):
        bot = self.bot
        """Views the user's wallet"""
        # Gets the user's wallet
        wallet = self.action_object.get_wallet(interaction.user.id)["data"]
        embed = discord.Embed(title="Wallet",
                              description="**Balance**: ₹{0}".format(
                                  wallet["balance"])
                              )
        try:
            # Gets the user's accent color
            accent = await bot.fetch_user(interaction.user.id)
            accent = accent.accent_color
            if accent is not None:
                embed.color = accent
            else:
                # Might occur if the user has 10 dollar nitro
                embed.color = 0xc6be0f
        except:
            embed.color = 0xc6be0f

        # Sets the embed's thumbnail to the user's avatar
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        # Sets the embed's author to the user's name and discriminator
        embed.set_author(name=interaction.user.name+"#" +
                         interaction.user.discriminator)
        # Sets the embed's footer to the user's ID
        embed.set_footer(text="ID: {0}".format(wallet["user_id"]))

        # Sends the embed
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="refresh", description="Refreshes all unpaid invoices. Also cancels any unpaid invoices")
    @app_commands.checks.cooldown(1, 3600, key=lambda i: (i.guild, i.user.id))
    @Checkers.is_dm()
    async def refresh_invoices(self, interaction: discord.Interaction):
        """Refreshes the invoices for the user."""
        # Get the user's invoices
        from payments import Payment
        from razorpay_custom import Razorpay
        await interaction.response.send_message("Refreshing your invoices...")
        transactions_obj = self.action_object.get_transactions(
            interaction.user.id)
        transactions = transactions_obj["data"]
        for t in transactions["reloads"]:
            i = transactions["reloads"][t]
            PAYMENTS_CLASS = None
            stat = i["status"]
            if t.endswith("RC"):
                PAYMENTS_CLASS = Payment
            elif t.endswith("RR"):
                PAYMENTS_CLASS = Razorpay
            if stat == "PAID" or stat == "VOID" or stat == "CANCELLED":
                continue
            else:
                new_stat = PAYMENTS_CLASS.check_payments(i['invoice'], True)
                if new_stat == "PAID":
                    transactions["reloads"][t]["status"] = "PAID"
                    self.action_object.add_balance(
                        interaction.user.id, i["amount"])
                    await interaction.followup.send(f"Invoice {i['invoice']}: Your wallet has been recharged with INR {i['amount']}")
                elif new_stat == "OPEN" or new_stat == "VIEWED" or new_stat == 'CREATED':
                    PAYMENTS_CLASS.void_payment(i['invoice'], True)
                    await interaction.followup.send(f"Invoice {i['invoice']}: Your invoice has been voided.")
                    if new_stat == 'CREATED':
                        transactions["reloads"][t]["status"] = "CANCELLED"
                        continue
                    transactions["reloads"][t]["status"] = "VOID"
                elif new_stat != stat:
                    transactions["reloads"][t]["status"] = new_stat
                    await interaction.followup.send(f"Invoice {i['invoice']}: Your invoice status is {new_stat}")
                else:
                    continue
        json.dump(transactions, open(
            transactions_obj["filepath"], "w"), indent=4)
        await interaction.followup.send("Your invoices have been refreshed.")

    @refresh_invoices.error
    async def refresh_invoices_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"Please wait for {error.retry_after} seconds before using this command again.", ephemeral=True)
        elif isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("Works in DMs only!", ephemeral=True)
        else:
            await interaction.response.send_message("An unknown error occured, please try again later.", ephemeral=True)
