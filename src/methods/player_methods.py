
import os
from flask import request, jsonify, render_template
from flask_jwt_simple import create_jwt, decode_jwt, get_jwt
from sqlalchemy import desc
from utils import APIException, check_params, validation_link, update_table, sha256, role_jwt_required
from models import db, Users, Profiles, Tournaments, Swaps, Flights, Buy_ins, Transactions, Tokens

def attach(app):
    
    
    @app.route('/users/<id>/email', methods=['PUT'])
    @role_jwt_required(['user'])
    def update_email(id):

        if id == 'me':
            id = str(get_jwt()['sub'])

        if not id.isnumeric():
            raise APIException('Invalid id: ' + id, 400)

        body = request.get_json()
        check_params(body, 'email', 'password', 'new_email')

        user = Users.query.filter_by( id=int(id), email=body['email'], password=sha256(body['password']) ).first()
        if user is None:
            raise APIException('Invalid parameters', 400)

        user.valid = False
        user.email = body['new_email']

        db.session.commit()

        return jsonify({
            'message': 'Please verify your new email',
            'validation_link': validation_link(user.id)
        }), 200




    @app.route('/users/reset_password/<token>', methods=['GET','PUT'])
    def html_reset_password(token):

        jwt_data = decode_jwt(token)
        if jwt_data['role'] != 'password':
            raise APIException('Access denied', 401)

        if request.method == 'GET':
            return render_template('reset_password.html',
                host = os.environ.get('API_HOST'),
                token = token
            )

        # request.method == 'PUT'
        body = request.get_json()
        check_params(body, 'email', 'password')

        user = Users.query.filter_by(id = jwt_data['sub'], email = body['email']).first()
        if user is None:
            raise APIException('User not found', 404)

        user.password = sha256(body['password'])

        db.session.commit()

        return jsonify({'message': 'Your password has been updated'}), 200




    @app.route('/users/<id>/password', methods=['PUT'])
    @role_jwt_required(['user'])
    def reset_password(id):

        if id == 'me':
            id = str(get_jwt())['sub']

        if not id.isnumeric():
            raise APIException('Invalid id: ' + id, 400)


        if request.args.get('forgot') == 'true':
            return jsonify({
                'message': 'A link has been sent to your email to reset the password',
                'link': os.environ.get('API_HOST') + '/users/reset_password/' + create_jwt({'id':id, 'role':'password'})
            }), 200


        body = request.get_json()
        check_params(body, 'email', 'password', 'new_password')

        user = Users.query.filter_by( id=int(id), email=body['email'], password=sha256(body['password']) ).first()
        if user is None:
            raise APIException('Invalid parameters', 400)

        user.password = sha256(body['new_password'])

        db.session.commit()

        return jsonify({'message': 'Your password has been changed'}), 200




    # id can be the user id, 'me' or 'all'
    @app.route('/profiles/<id>', methods=['GET'])
    @role_jwt_required(['user'])
    def get_profiles(id):

        jwt_data = get_jwt()

        if id == 'all':
            if jwt_data['role'] != 'admin':
                raise APIException('Access denied', 401)

            return jsonify([x.serialize(long=True) for x in Profiles.query.all()]), 200

        if id == 'me':
            id = str(jwt_data['sub'])

        if not id.isnumeric():
            raise APIException('Invalid id: ' + id, 400)

        user = Profiles.query.get(int(id))
        if user is None:
            raise APIException('User not found', 404)

        return jsonify(user.serialize(long=True)), 200




    @app.route('/profiles', methods=['POST'])
    @role_jwt_required(['user'])
    def register_profile():

        user = Users.query.get(get_jwt()['sub'])
        if user is None:
            raise APIException('User not found', 404)

        body = request.get_json()
        check_params(body, 'first_name', 'last_name')

        db.session.add(Profiles(
            first_name = body['first_name'],
            last_name = body['last_name'],
            nickname = body['nickname'] if 'nickname' in body else None,
            hendon_url = body['hendon_url'] if 'hendon_url' in body else None,
            user = user
        ))
        db.session.commit()

        return jsonify({'message':'ok'}), 200




    @app.route('/profiles/<id>', methods=['PUT'])
    @role_jwt_required(['user'])
    def update_profile(id):

        if id == 'me':
            id = str(get_jwt())['sub']

        if not id.isnumeric():
            raise APIException('Invalid id: ' + id, 400)

        prof = Profiles.query.get(int(id))
        if prof is None:
            raise APIException('User not found', 404)

        body = request.get_json()
        check_params(body)

        update_table(prof, body, ignore=['profile_pic_url'], action=actions.update_user)

        db.session.commit()

        return jsonify(prof.serialize())




    @app.route('/profiles/image', methods=['PUT'])
    @role_jwt_required(['user'])
    def update_profile_image():

        user = Users.query.get(get_jwt()['sub'])
        if user is None:
            raise APIException('User not found', 404)

        if 'image' not in request.files:
            raise APIException('Image property missing on the files array', 404)

        result = cloudinary.uploader.upload(
            request.files['image'],
            public_id='profile' + str(user.id),
            crop='limit',
            width=450,
            height=450,
            eager=[{
                'width': 200, 'height': 200,
                'crop': 'thumb', 'gravity': 'face',
                'radius': 100
            },
            ],
            tags=['profile_picture']
        )

        user.profile.profile_pic_url = result['secure_url']

        db.session.commit()

        return jsonify({'message':'ok'}), 200




    @app.route('/me/buy_ins', methods=['POST'])
    @role_jwt_required(['user'])
    def create_buy_in():

        body = request.get_json()
        check_params(body, 'flight_id', 'chips', 'table', 'seat')

        id = int(get_jwt()['sub'])

        prof = Profiles.query.get(id)
        if prof is None:
            raise APIException('User not found', 404)

        buyin = Buy_ins(
            user_id = id,
            flight_id = body['flight_id'],
            chips = body['chips'],
            table = body['table'],
            seat = body['seat']
        )
        db.session.add(buyin)
        db.session.commit()

        name = prof.nickname if prof.nickname else f'{prof.first_name} {prof.last_name}'

        buyin = Buy_ins.query.filter_by(
            user_id = id,
            flight_id = body['flight_id'],
            chips = body['chips'],
            table = body['table'],
            seat = body['seat']
        ).order_by(Buy_ins.id.desc()).first()

        return jsonify({ **buyin.serialize(), "name": name }), 200




    @app.route('/me/buy_ins/<int:id>', methods=['PUT'])
    @role_jwt_required(['user'])
    def update_buy_in(id):

        body = request.get_json()
        check_params(body)

        user_id = get_jwt()['sub']

        buyin = Buy_ins.query.get(id)

        if buyin is None:
            raise APIException('Buy_in not found', 404)

        update_table(buyin, body, ignore=['user_id','flight_id','receipt_img_url'])

        db.session.commit()

        return jsonify(Buy_ins.query.get(id).serialize())




    @app.route('/me/buy_ins/<int:id>/image', methods=['PUT'])
    @role_jwt_required(['user'])
    def update_buyin_image(id):

        user_id = get_jwt()['sub']

        buyin = Buy_ins.query.filter_by(id=id, user_id=user_id).first()
        if buyin is None:
            raise APIException('Buy_in not found', 404)

        if 'image' not in request.files:
            raise APIException('Image property missing on the files array', 404)

        result = cloudinary.uploader.upload(
            request.files['image'],
            public_id='buyin' + str(buyin.id),
            crop='limit',
            width=450,
            height=450,
            eager=[{
                'width': 200, 'height': 200,
                'crop': 'thumb', 'gravity': 'face',
                'radius': 100
            },
            ],
            tags=['buyin_picture','user_'+str(buyin.user_id),'buyin_'+str(buyin.id)]
        )

        buyin.receipt_img_url = result['secure_url']

        db.session.commit()

        return jsonify({'message':'ok'}), 200




    # Can search by id, 'name' or 'all'
    @app.route('/tournaments/<id>', methods=['GET'])
    @role_jwt_required(['user'])
    def get_tournaments(id):

        if id == 'all':
            return jsonify([x.serialize() for x in Tournaments.query.all()]), 200

        if id.isnumeric():
            trmnt = Tournaments.query.get(int(id))
        else:
            trmnt = Tournaments.query.filter( Tournaments.name.ilike(f'%{id}%') ).all()

        if trmnt is None:
            raise APIException('Tournament not found', 404)

        if isinstance(trmnt, list):
            return jsonify([x.serialize() for x in trmnt]), 200

        return jsonify(trmnt.serialize()), 200




    @app.route('/swaps/<id>', methods=['GET'])
    def get_swaps(id):

        if id == 'all':
            return jsonify([x.serialize() for x in Swaps.query.all()])

        prof = Profiles.query.get(7)
        return str(prof.available_percentage(1))
        # return jsonify( [x.serialize() for x in Swaps.query.all()] )




    @app.route('/me/swaps', methods=['POST'])
    @role_jwt_required(['user'])
    def create_swap():

        id = get_jwt()['sub']

        # get sender user
        sender = Profiles.query.get(id)
        if sender is None:
            raise APIException('User not found', 404)

        body = request.get_json()
        check_params(body, 'tournament_id', 'recipient_id', 'percentage')

        # get recipient user
        recipient = Profiles.query.get(body['recipient_id'])
        if recipient is None:
            raise APIException('Recipient user not found', 404)

        if Swaps.query.get((id, body['recipient_id'], body['tournament_id'])):
            raise APIException('Swap already exists, can not duplicate', 400)

        sender_availability = sender.available_percentage( body['tournament_id'] )
        if body['percentage'] > sender_availability:
            raise APIException(('Swap percentage too large. You can not exceed 50% per tournament. '
                                f'You have available: {sender_availability}%'), 400)

        recipient_availability = recipient.available_percentage( body['tournament_id'] )
        if body['percentage'] > recipient_availability:
            raise APIException(('Swap percentage too large for recipient. '
                                f'He has available to swap: {recipient_availability}%'), 400)

        db.session.add(Swaps(
            sender_id = id,
            tournament_id = body['tournament_id'],
            recipient_id = body['recipient_id'],
            percentage = body['percentage']
        ))
        db.session.add(Swaps(
            sender_id = body['recipient_id'],
            tournament_id = body['tournament_id'],
            recipient_id = id,
            percentage = body['percentage']
        ))
        db.session.commit()

        return jsonify({'message':'ok'}), 200




    # JSON receives a counter_percentage to update the swap of the recipient
    @app.route('/me/swaps', methods=['PUT'])
    @role_jwt_required(['user'])
    def update_swap():

        id = get_jwt()['sub']

        # get sender user
        sender = Profiles.query.get(id)
        if sender is None:
            raise APIException('User not found', 404)

        body = request.get_json()
        check_params(body, 'tournament_id', 'recipient_id')

        # get recipient user
        recipient = Profiles.query.get(body['recipient_id'])
        if recipient is None:
            raise APIException('Recipient user not found', 404)

        # get swap
        swap = Swaps.query.get((id, recipient.id, body['tournament_id']))
        counter_swap = Swaps.query.get((recipient.id, id, body['tournament_id']))
        if swap is None or counter_swap is None:
            raise APIException('Swap not found', 404)

        if 'percentage' in body:

            percentage = abs(body['percentage'])
            counter = abs(body['counter_percentage']) if 'counter_percentage' in body else percentage

            sender_availability = sender.available_percentage( body['tournament_id'] )
            if percentage > sender_availability:
                raise APIException(('Swap percentage too large. You can not exceed 50% per tournament. '
                                    f'You have available: {sender_availability}%'), 400)

            recipient_availability = recipient.available_percentage( body['tournament_id'] )
            if counter > recipient_availability:
                raise APIException(('Swap percentage too large for recipient. '
                                    f'He has available to swap: {recipient_availability}%'), 400)

            # So it can be updated correctly with the update_table funcion
            body['percentage'] = swap.percentage + percentage
            update_table(counter_swap, {'percentage': counter_swap.percentage + counter})

        update_table(swap, body, ignore=['tournament_id','recipient_id','paid','counter_percentage'])

        db.session.commit()

        return jsonify(swap.serialize())




    @app.route('/swaps/me/tournament/<int:id>', methods=['GET'])
    @role_jwt_required(['user'])
    def get_swaps_actions(id):

        user_id = get_jwt()['sub']

        prof = Profiles.query.get(user_id)
        if prof is None:
            raise APIException('User not found', 404)

        return jsonify(prof.get_swaps_actions(id))






    @app.route('/users/me/swaps/<id>/done', methods=['PUT'])
    @role_jwt_required(['user'])
    def set_swap_paid(id):

        id = get_jwt()['sub']

        # get sender user
        sender = Profiles.query.get(id)
        if sender is None:
            raise APIException('User not found', 404)

        body = request.get_json()
        check_params(body, 'tournament_id', 'recipient_id')

        swap = Swaps.query.get(id, body['recipient_id'], body['tournament_id'])

        swap.paid = True

        db.session.commit()

        return jsonify({'message':'Swap has been paid'})




    @app.route('/me/buy_ins', methods=['GET'])
    @role_jwt_required(['user'])
    def get_buy_in():
        
        id = get_jwt()['sub']

        buyin = Buy_ins.query.filter_by(user_id=id).order_by(Buy_ins.id.desc()).first()
        if buyin is None:
            raise APIException('Buy_in not found', 404)

        return jsonify(buyin.serialize()), 200




    @app.route('/me/swap_tracker', methods=['GET'])
    @role_jwt_required(['user'])
    def swap_tracker():

        id = get_jwt()['sub']

        trmnts = Tournaments.get_live(user_id=id)
        if trmnts:
            raise APIException('You have not bought into any current tournaments', 404)

        print([x.serialize() for x in trmnts])
        list_of_swap_trackers = []

        for trmnt in trmnts:

            my_buyin = Buy_ins.get_latest( user_id=id, tournament_id=trmnt.id )
            if my_buyin is None:
                raise APIException('Can not find buyin', 404)

            swaps = Swaps.query.filter_by(
                sender_id = id,
                tournament_id = trmnt.id
            )
            if swaps is None:
                return jsonify({'message':'You have no live swaps in this tournament'})

            swaps = [{
                'swap': swap.serialize(),
                'buyin': (Buy_ins.get_latest(
                                user_id = swap.recipient_id,
                                tournament_id=trmnt.id
                            ).serialize())
            } for swap in swaps]

            list_of_swap_trackers.append({
                'tournament': trmnt.serialize(),
                'my_buyin': my_buyin.serialize(),
                'swaps': swaps
            })
        print(list_of_swap_trackers)
        return jsonify(list_of_swap_trackers)




    return app