"""
Maps Banking77's 77 fine-grained banking intents to our 5 support
categories, so the dataset can train Router v2b.

HONEST METHODOLOGICAL CAVEAT (belongs in the capstone report too):
Banking77 is a banking-domain dataset; our taxonomy is for a retail
electronics support system. This mapping is a reasonable proxy based on
semantic similarity (e.g. "card fraud" -> complaint, "refund" -> billing),
not a perfect domain match. Treat v2b's accuracy numbers as a proof of
concept for the *training pipeline*, not a production-ready classifier
for TechMart-specific intents — it has never seen a TechMart-style query
at training time.

BANKING77_TO_DOMAIN keys must exactly match the 77 category strings from
the source CSV (case-sensitive) — completeness is checked in the training
script against the actual downloaded file, not assumed here.
"""

BANKING77_TO_DOMAIN: dict[str, str] = {
    # --- billing: payments, charges, fees, refunds, transfers, top-ups ---
    "transaction_charged_twice": "billing",
    "request_refund": "billing",
    "Refund_not_showing_up": "billing",
    "card_payment_fee_charged": "billing",
    "cash_withdrawal_charge": "billing",
    "exchange_charge": "billing",
    "exchange_rate": "billing",
    "extra_charge_on_statement": "billing",
    "top_up_by_bank_transfer_charge": "billing",
    "top_up_by_card_charge": "billing",
    "top_up_by_cash_or_cheque": "billing",
    "top_up_limits": "billing",
    "transfer_fee_charged": "billing",
    "transfer_into_account": "billing",
    "transfer_timing": "billing",
    "receiving_money": "billing",
    "balance_not_updated_after_bank_transfer": "billing",
    "balance_not_updated_after_cheque_or_cash_deposit": "billing",
    "pending_transfer": "billing",
    "pending_top_up": "billing",
    "cancel_transfer": "billing",
    "failed_transfer": "billing",
    "transfer_not_received_by_recipient": "billing",
    "wrong_amount_of_cash_received": "billing",
    "wrong_exchange_rate_for_cash_withdrawal": "billing",
    "card_payment_wrong_exchange_rate": "billing",
    "automatic_top_up": "billing",
    "topping_up_by_card": "billing",
    "top_up_failed": "billing",
    "top_up_reverted": "billing",
    "beneficiary_not_allowed": "billing",
    "declined_transfer": "billing",

    # --- technical: app/card malfunction, verification, PIN, ATM issues ---
    "card_not_working": "technical",
    "contactless_not_working": "technical",
    "virtual_card_not_working": "technical",
    "card_swallowed": "technical",
    "atm_support": "technical",
    "declined_card_payment": "technical",
    "declined_cash_withdrawal": "technical",
    "pending_card_payment": "technical",
    "pending_cash_withdrawal": "technical",
    "card_linking": "technical",
    "exchange_via_app": "technical",
    "passcode_forgotten": "technical",
    "pin_blocked": "technical",
    "change_pin": "technical",
    "unable_to_verify_identity": "technical",
    "verify_my_identity": "technical",
    "verify_source_of_funds": "technical",
    "verify_top_up": "technical",
    "why_verify_identity": "technical",
    "card_acceptance": "technical",

    # --- complaint: fraud, security concerns, dissatisfaction, lost/stolen ---
    "compromised_card": "complaint",
    "lost_or_stolen_card": "complaint",
    "lost_or_stolen_phone": "complaint",
    "card_payment_not_recognised": "complaint",
    "cash_withdrawal_not_recognised": "complaint",
    "direct_debit_payment_not_recognised": "complaint",
    "terminate_account": "complaint",
    "reverted_card_payment?": "complaint",

    # --- product: card types, features, limits (closest banking analog
    #     to "product specs" in a retail context) ---
    "visa_or_mastercard": "product",
    "get_physical_card": "product",
    "get_disposable_virtual_card": "product",
    "getting_virtual_card": "product",
    "getting_spare_card": "product",
    "order_physical_card": "product",
    "disposable_card_limits": "product",
    "supported_cards_and_currencies": "product",
    "fiat_currency_support": "product",
    "apple_pay_or_google_pay": "product",
    "card_about_to_expire": "product",
    "card_delivery_estimate": "product",
    "card_arrival": "product",
    "country_support": "product",

    # --- faq: general account info / policy ---
    "age_limit": "faq",
    "edit_personal_details": "faq",
    "activate_my_card": "faq",
}
