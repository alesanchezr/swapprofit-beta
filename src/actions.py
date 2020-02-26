from models import Profiles, Buy_ins, Swaps


def swap_tracker_json(trmnt, user_id):
    
    my_buyin = Buy_ins.get_latest( user_id=user_id, tournament_id=trmnt.id )
    final_profit = 0

    swaps = Swaps.query.filter_by(
        sender_id = user_id,
        tournament_id = trmnt.id
    )

    # separate swaps by recipient
    swaps_by_recipient = {}
    for swap in swaps:
        rec_id = str(swap.recipient_id)
        data = swaps_by_recipient.get( rec_id, [] )
        swaps_by_recipient[ rec_id ] = [ *data, swap ]
    

    swaps_buyins = []
    for rec_id, swaps in swaps_by_recipient.items():
        recipient_buyin = Buy_ins.get_latest(
                user_id = rec_id,
                tournament_id = trmnt.id
            )

        # Catch ERRORS
        if recipient_buyin is None or my_buyin is None:
            swap_data_for_error_message = [{
                'recipient_name': f'{x.recipient_user.first_name} {x.recipient_user.last_name}',
                'sender_name': f'{x.sender_user.first_name} {x.sender_user.last_name}',
                'tournament_name': x.tournament.name 
            } for x in swaps]
            if recipient_buyin is None:
                return { 
                    'ERROR':'Recipient has swaps with user in this tournament but no buy-in',
                    'recipient buyin': None,
                    'swaps with user': swap_data_for_error_message }
            if my_buyin is None:
                return { 
                    'ERROR':'User has swaps in this tournament but no buy-in',
                    'buyin': None,
                    'user swaps': swap_data_for_error_message }


        recipient_user = Profiles.query.get( rec_id )
        data = {
            'recipient_user': recipient_user.serialize(),
            'recipient_buyin': recipient_buyin.serialize(),
            'their_place': recipient_buyin.place,
            'you_won': my_buyin.winnings if my_buyin.winnings else 0,
            'they_won': recipient_buyin.winnings if recipient_buyin.winnings else 0,
            'available_percentage': recipient_user.available_percentage(),
            'agreed_swaps': [],
            'other_swaps': []
        }


        you_owe_total = 0
        they_owe_total = 0
        for swap in swaps:
            you_owe = (my_buyin.winnings * swap.percentage / 100) \
                if my_buyin.winnings is not None else 0
            they_owe = (recipient_buyin.winnings * swap.counter_swap.percentage / 100) \
                if recipient_buyin.winnings is not None else 0
            you_owe_total += you_owe
            they_owe_total += they_owe
            single_swap_data = {
                'counter_percentage': swap.counter_swap.percentage,
                'you_owe': you_owe,
                'they_owe': they_owe,
                **swap.serialize()
            }
            if swap.status._value_ == 'agreed':
                data['agreed_swaps'].append(single_swap_data)
            else:
                data['other_swaps'].append(single_swap_data)


        data['you_owe_total'] = you_owe_total
        data['they_owe_total'] = they_owe_total
        final_profit -= you_owe_total
        final_profit += they_owe_total

        swaps_buyins.append(data)


    return {
        'tournament': trmnt.serialize(),
        'my_buyin': my_buyin and my_buyin.serialize(),
        'buyins': swaps_buyins,
        'final_profit': final_profit
    }