import os
import ocr
import json
import cloudinary
import cloudinary.uploader
from google.cloud import vision
from datetime import datetime, timedelta
from flask import request, jsonify, render_template
from flask_jwt_simple import create_jwt, decode_jwt, get_jwt
from sqlalchemy import desc, asc
from utils import (APIException, check_params, jwt_link, update_table, 
    sha256, role_jwt_required, resolve_pagination, isFloat)
from models import (db, Users, Profiles, Tournaments, Swaps, Flights, 
    Buy_ins, Transactions, Devices)
from notifications import send_email, send_fcm


def attach(app):
    
    
    @app.route('/users/me/email', methods=['PUT'])
    @role_jwt_required(['user'])
    def update_email(user_id):
        
        req = request.get_json()
        check_params(req, 'email', 'password', 'new_email')

        if req['email'] == req['new_email']:
            return jsonify({'message':'Your email is already '+req['new_email']})

        user = Users.query.filter_by( 
            id = user_id, 
            email = req['email'], 
            password = sha256(req['password']) 
        ).first()
        
        if user is None:
            raise APIException('User not found', 404)

        user.status._value_ = 'invalid'
        user.email = req['new_email']

        db.session.commit()

        send_email( template='email_validation', emails=user.email, 
            data={'validation_link': jwt_link(user.id, role='email_change')} )

        return jsonify({'message': 'Please verify your new email'}), 200




    @app.route('/users/reset_password/<token>', methods=['GET','PUT'])
    def html_reset_password(token):

        jwt_data = decode_jwt(token)
        
        if request.method == 'GET':
            user = Users.query.filter_by(
                id = jwt_data['sub'], 
                email = jwt_data['role']).first()
            if user is None:
                raise APIException('User not found', 404)

            return render_template('reset_password.html',
                host = os.environ.get('API_HOST'),
                token = token,
                email = jwt_data['role']
            )
        
        # request.method == 'PUT'
        req = request.get_json()
        check_params(req, 'email', 'password')

        user = Users.query.filter_by(
            id = jwt_data['sub'],
            email = req['email']
        )
        if user is None:
            raise APIException('User not found', 404)

        user.password = sha256(req['password'])

        db.session.commit()

        return jsonify({'message': 'Your password has been updated'}), 200




    @app.route('/users/me/password', methods=['PUT'])
    def reset_password():

        req = request.get_json()
        check_params(req, 'email')

        # User forgot their password
        if request.args.get('forgot') == 'true':
            user = Users.query.filter_by( email=req['email'] ).first()
            if user is None:
                raise APIException('This email is not registered', 400)

            send_email('reset_password_link', emails=req['email'], 
                data={'link':jwt_link(user.id, '/users/reset_password/', req['email'])})
            return jsonify({
                'message': 'A link has been sent to your email to reset the password',
                'link': jwt_link(user.id, '/users/reset_password/', req['email'])
            }), 200

        # User knows their password
        check_params(req, 'password', 'new_password')

        user = Users.query.filter_by(
            email=req['email'],
            password=sha256(req['password'])
        ).first()
        if user is None:
            raise APIException('User not found', 404)

        user.password = sha256(req['new_password'])

        db.session.commit()

        return jsonify({'message': 'Your password has been changed'}), 200




    @app.route('/users/invite', methods=['POST'])
    @role_jwt_required(['user'])
    def invite_users(user_id):

        req = request.get_json()
        check_params(req, 'email')

        user = Users.query.get( user_id )

        send_email('invitation_email', emails=req['email'], data={
            'user_name': f'{user.first_name} {user.last_name}'
        })

        return jsonify({'message':'Invitation sent successfully'})




    # id can be the user id, 'me' or 'all'
    @app.route('/profiles/<id>', methods=['GET'])
    @role_jwt_required(['user'])
    def get_profiles(user_id, id):
        
        jwt_data = get_jwt()

        if id == 'all':
            if jwt_data['role'] != 'admin':
                raise APIException('Access denied', 403)

            return jsonify([x.serialize() for x in Profiles.query.all()]), 200

        if id == 'me':
            id = str(user_id)

        if not id.isnumeric():
            raise APIException('Invalid id: ' + id, 400)

        user = Profiles.query.get(int(id))
        if user is None:
            raise APIException('User not found', 404)

        return jsonify(user.serialize()), 200




    @app.route('/profiles', methods=['POST'])
    @role_jwt_required(['user'])
    def register_profile(user_id):

        user = Users.query.get(user_id)

        req = request.get_json()
        check_params(req, 'first_name', 'last_name')

        db.session.add(Profiles(
            first_name = req['first_name'],
            last_name = req['last_name'],
            nickname = req.get('nickname'),
            hendon_url = req.get('hendon_url'),
            user = user
        ))
        db.session.commit()

        return jsonify({'message':'ok'}), 200

      
      
      
    @app.route('/profiles/me', methods=['PUT'])
    @role_jwt_required(['user'])
    def update_profile(user_id):

        prof = Profiles.query.get(user_id)

        req = request.get_json()
        check_params(req)

        update_table(prof, req, ignore=['profile_pic_url'])

        db.session.commit()

        return jsonify(prof.serialize())




    @app.route('/profiles/image', methods=['PUT'])
    @role_jwt_required(['user'])
    def update_profile_image(user_id):

        user = Users.query.get(user_id)

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
            }],
            tags=['profile_picture']
        )

        user.profile.profile_pic_url = result['secure_url']

        db.session.commit()

        return jsonify({'profile_pic_url': result['secure_url']}), 200




    @app.route('/me/buy_ins', methods=['GET'])
    @role_jwt_required(['user'])
    def get_buy_in(user_id):
        
        buyin = Buy_ins.query.filter_by(user_id=user_id).order_by(Buy_ins.id.desc()).first()
        if buyin is None:
            raise APIException('Buy_in not found', 404)

        return jsonify(buyin.serialize()), 200




    @app.route('/me/buy_ins', methods=['POST'])
    @role_jwt_required(['user'])
    def create_buy_in(user_id):

        req = request.get_json()
        check_params(req, 'flight_id')

        buyin = Buy_ins(
            user_id = user_id,
            flight_id = req['flight_id']
        )
        db.session.add(buyin)
        db.session.commit()
        
        prof = Profiles.query.get(user_id)
        name = prof.nickname if prof.nickname else f'{prof.first_name} {prof.last_name}'

        return jsonify({ 
            'buyin_id': buyin.id, 
            'name': name 
        }), 200


        

    @app.route('/me/buy_ins/<int:id>', methods=['PUT'])
    @role_jwt_required(['user'])
    def update_buy_in(user_id, id):

        req = request.get_json()
        check_params(req)

        buyin = Buy_ins.query.filter_by(id=id, user_id=user_id).first()

        if buyin is None:
            raise APIException('Buy_in not found', 404)

        update_table(buyin, req, 
            ignore=['user_id','flight_id','receipt_img_url','place'])

        db.session.commit()
        
        return jsonify(buyin.serialize())




    @app.route('/me/buy_ins/<int:id>/image', methods=['PUT'])
    @role_jwt_required(['user'])
    def update_buyin_image(user_id, id):

        buyin = Buy_ins.query.filter_by(id=id, user_id=user_id).first()
        if buyin is None:
            raise APIException('Buy_in not found', 404)


        if request.args.get('review') == 'true':

            req = request.get_json()
            check_params(req, 'chips','table','seat')

            buyin.chips = req.get('chips')
            buyin.table = req.get('table')
            buyin.seat = req.get('seat')
            db.session.commit()

            send_email(template='buyin_receipt', emails=buyin.user.user.email,
            data={
                'receipt_url': buyin.receipt_img_url,
                'tournament_date': buyin.flight.tournament.start_at,
                'tournament_name': buyin.flight.tournament.name
            })

            return jsonify({'message':'Buy in saved. Email sent'})



        if 'image' not in request.files:
            raise APIException('Image property missing in the files array', 404)

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
            }],
            tags=[
                'buyin_receipt',
                'user_'+ str(user_id),
                'buyin_'+ str(buyin.id)
            ]
        )
        
        buyin.receipt_img_url = result['secure_url']
        db.session.commit()

        client = vision.ImageAnnotatorClient()
        image = vision.types.Image()
        image.source.image_uri = result['secure_url']

        response = client.text_detection(image=image)
        texts = response.text_annotations
        text = texts[0].description
        
        cloudinary.uploader.destroy('buyin' + str(buyin.id))

        receipt_data = ocr.hard_rock(text)

        if receipt_data['tournament_name'] is None or receipt_data['date'] is None:
            raise APIException('Can not read picture, take another', 500)

        # Validate buyin receipt w tournament name and flight start_at
        now = datetime.utcnow
        if (now - buyin.flight.start_at) > timedelta(hours=17) and \
            receipt_data['tournament_name'] != buyin.flight.tournament.name:
        
            send_email(template='wrong_receipt', emails=buyin.user.user.email,
                data={
                    'receipt_url': buyin.receipt_img_url,
                    'tournament_date': buyin.flight.tournament.start_at,
                    'tournament_name': buyin.flight.tournament.name,
                    'upload_time': result['created_at']
                })
            raise APIException('Wrong receipt was upload', 400)


        return jsonify(receipt_data)




    @app.route('/tournaments/<id>', methods=['GET'])
    @role_jwt_required(['user'])
    def get_tournaments(user_id, id):

        if id == 'all':
            now = datetime.utcnow() - timedelta(days=1)

            # Filter past tournaments
            if request.args.get('history') == 'true':
                trmnts = Tournaments.get_history()

            # Filter current and future tournaments
            else:
                trmnts = Tournaments.get_live_upcoming()
                    
            # Filter by name
            name = request.args.get('name') 
            if name is not None:
                trmnts = trmnts.filter( Tournaments.name.ilike(f'%{name}%') )


            # Order by zip code
            zip = request.args.get('zip', '')
            if zip.isnumeric():
                with open(os.getcwd()+'/src/zip_codes.json') as zip_file:
                    data = json.load(zip_file)
                    zipcode = data.get(zip)
                    if zipcode is None:
                        raise APIException('Zipcode not in file', 500)
                    lat = zipcode['latitude']
                    lon = zipcode['longitude']

            # Order by user location
            else:
                lat = request.args.get('lat', '')
                lon = request.args.get('lon', '')

            if isFloat(lat) and isFloat(lon):
                trmnts = trmnts.order_by( 
                    ( db.func.abs(float(lon) - Tournaments.longitude) + 
                      db.func.abs(float(lat) - Tournaments.latitude) )
                .asc() )

            # Order by ascending date
            elif request.args.get('asc') == 'true':
                trmnts = trmnts.order_by( Tournaments.start_at.asc() )

            # Order by descending date
            elif request.args.get('desc') == 'true':
                trmnts = trmnts.order_by( Tournaments.start_at.desc() )

            
            # Pagination
            offset, limit = resolve_pagination( request.args )
            trmnts = trmnts.offset( offset ).limit( limit )

            
            return jsonify([x.serialize() for x in trmnts]), 200


        # Single tournament by id
        elif id.isnumeric():
            trmnt = Tournaments.query.get(int(id))
            if trmnt is None:
                raise APIException('Tournament not found', 404)

            return jsonify(trmnt.serialize()), 200


        raise APIException('Invalid id', 400)




    @app.route('/me/swaps', methods=['POST'])
    @role_jwt_required(['user'])
    def create_swap(user_id):

        # Get sender user
        sender = Profiles.query.get(user_id)


        # Get request json
        req = request.get_json()
        check_params(req, 'tournament_id', 'recipient_id', 'percentage')

        swap_cost = abs( req.get('cost', 1) )
        if sender.get_coins() < swap_cost:
            raise APIException('Insufficient coins to make this swap', 402)

        percentage = abs( req['percentage'] )
        counter = abs( req.get('counter_percentage', percentage) )


        # Get recipient user
        recipient = Profiles.query.get( req['recipient_id'] )
        if recipient is None:
            raise APIException('Recipient user not found', 404)


        # Check tournament existance
        trmnt = Tournaments.query.get( req['tournament_id'] )
        if trmnt is None:
            raise APIException('Tournament not found', 404)


        # Availability
        sender_availability = sender.available_percentage( req['tournament_id'] )
        if percentage > sender_availability:
            raise APIException(('Swap percentage too large. You can not exceed 50% per tournament. '
                                f'You have available: {sender_availability}%'), 400)

        recipient_availability = recipient.available_percentage( req['tournament_id'] )
        if counter > recipient_availability:
            raise APIException(('Swap percentage too large for recipient. '
                                f'He has available to swap: {recipient_availability}%'), 400)


        s1 = Swaps(
            sender_id = user_id,
            tournament_id = req['tournament_id'],
            recipient_id = recipient.id,
            percentage = percentage,
            cost = swap_cost,
            status = 'pending'
        )
        s2 = Swaps(
            sender_id = recipient.id,
            tournament_id = req['tournament_id'],
            recipient_id = user_id,
            percentage = counter,
            cost = swap_cost,
            status = 'incoming',
            counter_swap = s1
        )
        s1.counter_swap = s2
        
        db.session.add_all([s1, s2])
        db.session.commit()

        # send_fcm('swap_incoming_notification', recipient.id)

        return jsonify({'message':'Swap created successfully.'}), 200




    @app.route('/me/swaps/<int:id>', methods=['PUT'])
    @role_jwt_required(['user'])
    def update_swap(user_id, id):

        # Get sender user
        sender = Profiles.query.get(user_id)

        req = request.get_json()
        check_params(req)
        

        # Get swaps
        swap = Swaps.query.get(id)
        if sender.id != swap.sender_id:
            raise APIException('This user has no access to this swap. ' +
                                'Try swap id: ' + swap.counter_swap_id, 401)

        if sender.get_coins() < swap.cost:
            raise APIException('Insufficient coins to see this swap', 402)

        unpermitted_status = ['canceled','rejected','agreed']
        if swap.status._value_ in unpermitted_status:
            raise APIException('This swap can not be modified', 400)

        counter_swap_body = {}
        counter_swap = Swaps.query.get( swap.counter_swap_id )
        if swap is None or counter_swap is None:
            raise APIException('Swap not found', 404)


        # Get recipient user
        recipient = Profiles.query.get( swap.recipient_id )
        if recipient is None:
            raise APIException('Recipient user not found', 404)


        if 'percentage' in req:
            percentage = abs( req['percentage'] )
            counter = abs( req.get('counter_percentage', percentage) )

            sender_availability = sender.available_percentage( swap.tournament_id )
            if percentage > sender_availability:
                raise APIException(('Swap percentage too large. You can not exceed 50% per tournament. '
                                    f'You have available: {sender_availability}%'), 400)

            recipient_availability = recipient.available_percentage( swap.tournament_id )
            if counter > recipient_availability:
                raise APIException(('Swap percentage too large for recipient. '
                                    f'He has available to swap: {recipient_availability}%'), 400)
 
            new_percentage = swap.percentage + percentage
            new_counter_percentage = counter_swap.percentage + counter

            # So it can be updated correctly with the update_table funcion
            req['percentage'] = new_percentage

            counter_swap_body['percentage'] = new_counter_percentage


        if 'status' in req:
            status = req.get('status')

            if status == 'agreed' and swap.status._value_ == 'pending':
                raise APIException('Can not agree a swap on a pending status', 400)
            
            counter_swap_body['status'] = Swaps.counter_status( status )

            # send_fcm('swap_incoming_notification', recipient.id)


        update_table( swap, req, ignore=['tournament_id','recipient_id','paid','counter_percentage','cost'])
        update_table( counter_swap, counter_swap_body )

        db.session.commit()


        if req.get('status') == 'agreed':

            if recipient.get_coins() < swap.cost:
                raise APIException('Recipient has insufficient coins to process this swap')

            db.session.add( Transactions(
                user_id = user_id,
                dollars = 0,
                coins = -swap.cost
            ))
            db.session.add( Transactions(
                user_id = recipient.id,
                dollars = 0,
                coins = -swap.cost
            ))
            db.session.commit()

            # send_fcm('swap_agreed_notificatin', recipient.id)

            send_email( template='swap_confirmation', emails=[sender.user.email, recipient.user.email],
                data={
                    'tournament_date': swap.tournament.start_at,
                    'tournament_name': swap.tournament.name,
                    
                    'user1_name': f'{sender.first_name} {sender.last_name}',
                    'user1_prof_pic': sender.profile_pic_url,
                    'user1_percentage': swap.percentage,
                    'user1_receipt_url': Buy_ins.get_latest(sender.id, swap.tournament_id).receipt_img_url,

                    'user2_name': f'{recipient.first_name} {recipient.last_name}',
                    'user2_prof_pic': recipient.profile_pic_url,
                    'user2_percentage': counter_swap.percentage,
                    'user2_receipt_url': Buy_ins.get_latest(recipient.id, swap.tournament_id).receipt_img_url
                })

        return jsonify([
            swap.serialize(),
            counter_swap.serialize()
        ])




    @app.route('/swaps/me/tournament/<int:id>', methods=['GET'])
    @role_jwt_required(['user'])
    def get_swaps_actions(user_id, id):

        prof = Profiles.query.get(user_id)

        return jsonify(prof.get_swaps_actions(id))




    @app.route('/users/me/swaps/<int:id>/done', methods=['PUT'])
    @role_jwt_required(['user'])
    def set_swap_paid(user_id, id):

        sender = Profiles.query.get(user_id)

        req = request.get_json()
        check_params(req, 'tournament_id', 'recipient_id')

        swap = Swaps.query.get(id)
        if req['tournament_id'] !=  swap.tournament_id \
            or req['recipient_id'] != swap.recipient_id:
            raise APIException('IDs do not match', 400)

        if swap.status._value_ != 'agreed':
            raise APIException('This swap has not been agreed upon', 400)

        swap.paid = True

        db.session.commit()

        return jsonify({'message':'Swap has been paid'})




    @app.route('/me/swap_tracker', methods=['GET'])
    @role_jwt_required(['user'])
    def swap_tracker(user_id):
        
        if request.args.get('history') == 'true':
            trmnts = Tournaments.get_history(user_id=user_id)
        else:
            trmnts = Tournaments.get_live_upcoming(user_id=user_id)

        swap_trackers = []

        if trmnts is not None:
            
            for trmnt in trmnts:

                my_buyin = Buy_ins.get_latest( user_id=user_id, tournament_id=trmnt.id )

                swaps = Swaps.query.filter_by(
                    sender_id = user_id,
                    tournament_id = trmnt.id
                )

                swaps_buyins = [{
                    'swap': swap.serialize(),
                    'buyin': Buy_ins.get_latest(
                                user_id = swap.recipient_id,
                                tournament_id = trmnt.id
                            ).serialize()
                } for swap in swaps]

                swap_trackers.append({
                    'tournament': trmnt.serialize(),
                    'my_buyin': my_buyin.serialize(),
                    'swaps': swaps_buyins
                })

        return jsonify( swap_trackers )




    @app.route('/users/me/devices', methods=['POST','DELETE'])
    @role_jwt_required(['user'])
    def add_device(user_id):
        
        req = request.get_json()
        check_params(req, 'token')

        if request.method == 'DELETE':
            device = Buy_ins.query.filter_by( token=req['token'] )
            if device is not None:
                db.session.delete( device )
                db.session.commit()
            
            return jsonify({'message':'Device deleted successfully'})
            

        db.session.add(Devices(
            user_id = user_id,
            token = req['token']
        ))
        db.session.commit()

        return jsonify({'message':'Device added successfully'})




    @app.route('/users/me/transaction', methods=['POST'])
    @role_jwt_required(['user'])
    def add_coins(user_id):

        req = request.get_json()
        check_params(req, 'coins')

        db.session.add( Transactions(
            user_id = user_id,
            coins = req['coins'],
            dollars = req.get('dollars', 0)
        ))

        db.session.commit()

        user = Users.query.get(user_id)
        return jsonify({'total_coins': user.get_total_coins()})




    @app.route('/users/me/transaction/report', methods=['GET'])
    @role_jwt_required(['user'])
    def transaction_report(user_id):
        
        month_ago = datetime.utcnow() - timedelta(months=1)

        report = Transactions.query \
                    .filter( Transaction.created_at > month_ago ) \
                    .order_by( Transactions.created_at.desc() )

        return jsonify([x.serialize() for x in report])



    return app
