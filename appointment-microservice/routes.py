import datetime
import requests
import sqlalchemy
from flask import request, jsonify
from flask_cors import CORS
from flask_jwt_extended import jwt_required, get_jwt_identity, JWTManager

from models import db, Appointment

# CORS
CORS_ORIGINS = [
    'http://localhost:3000',
    'http://auth-microservice:5000',
    'http://patient-microservice:5001',
    'http://doctor-microservice:5002'
]
cors = CORS(origins=CORS_ORIGINS)
# JWT
jwt = JWTManager()

def get_patient(user_id):
    patient_url = f'http://patient-microservice:5001/get-patient/user/{user_id}'
    patient_response = requests.get(patient_url, headers={'Authorization': request.headers['Authorization']})
    patient = patient_response.json()
    return patient

def get_patient_by_id(patient_id):
    patient_url = f'http://patient-microservice:5001/get-patient/{patient_id}'
    patient_response = requests.get(patient_url, headers={'Authorization': request.headers['Authorization']})
    patient = patient_response.json()
    return patient

def get_doctor(user_id):
    doctor_url = f'http://doctor-microservice:5002/get-doctor/user/{user_id}'
    doctor_response = requests.get(doctor_url, headers={'Authorization': request.headers['Authorization']})
    doctor = doctor_response.json()
    return doctor

def get_doctor_by_id(doctor_id):
    doctor_url = f'http://doctor-microservice:5002/get-doctor/{doctor_id}'
    doctor_response = requests.get(doctor_url, headers={'Authorization': request.headers['Authorization']})
    doctor = doctor_response.json()
    return doctor

def get_patient_id(user_id):
    patient = get_patient(user_id)
    patient_id = patient['id']
    return patient_id

def get_patient_name(user_id):
    patient = get_patient(user_id)
    patient_name = patient['firstName'] + ' ' + patient['lastName']
    return patient_name

def get_patient_address(patient_id):
    patient = get_patient_by_id(patient_id)
    address = patient['address']
    return address

def get_patient_date_of_birth(patient_id):
    patient = get_patient_by_id(patient_id)
    date_of_birth = patient['dateOfBirth']
    return date_of_birth

def get_patient_phone_number(patient_id):
    patient = get_patient_by_id(patient_id)
    phone_number = patient['phoneNumber']
    return phone_number

def get_doctor_id(user_id):
    doctor = get_doctor(user_id)
    doctor_id = doctor['id']
    return doctor_id

def get_doctor_name(doctor_id):
    doctor = get_doctor_by_id(doctor_id)
    doctor_name = doctor['firstName'] + ' ' + doctor['lastName']
    return doctor_name

def get_user_role():
    user_url = 'http://auth-microservice:5000/get-user'
    user_response = requests.get(user_url, headers={'Authorization': request.headers['Authorization']})
    user = user_response.json()
    user_role = user['role']
    return user_role

def app_routes(app):
    app_route_home(app)
    app_route_create_appointment(app)
    app_route_get_appointment_by_id(app)
    app_route_get_all_appointments(app)
    app_route_get_doctors_patients(app)
    app_route_delete_appointment(app)
    app_route_approve_appointment(app)
    app_route_reject_appointment(app)
    app_route_cancel_appointment(app)

# -------------------------------------------------------------------------------------------------------------------- #


# Home
def app_route_home(app):

    @app.route('/', methods=['GET'])
    def home():
        return jsonify(msg='Appointment service is up and running.'), 200


# Create appointment
def app_route_create_appointment(app):

    @app.route('/create-appointment', methods=['POST'])
    @jwt_required()
    def create_appointment():
        data = request.get_json()

        if 'doctorId' not in data or data['doctorId'] == '':
            return jsonify(error='Doctor ID is required.'), 400

        if 'date' not in data or data['date'] == '':
            return jsonify(error='Date is required.'), 400

        if 'time' not in data or data['time'] == '':
            return jsonify(error='Time is required.'), 400

        # getting patient id and patient name of current user
        user_id = get_jwt_identity()
        patient_id = get_patient_id(user_id)
        patient_name = get_patient_name(user_id)

        # getting selected doctor name
        doctor_id = data['doctorId']
        doctor_name = get_doctor_name(doctor_id)

        date = datetime.datetime.strptime(data['date'], '%Y-%m-%dT%H:%M:%S.%fZ')
        hours = data['time']['hours']
        minutes = data['time']['minutes']
        seconds = "00"
        time = f'{hours}:{minutes}:{seconds}'
        formated_time = datetime.datetime.strptime(time, '%H:%M:%S').time()

        new_appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            date=date,
            time=formated_time,
            patient_name=patient_name,
            doctor_name=doctor_name,
            status='na čekanju'
        )
        try:
            db.session.add(new_appointment)
            db.session.commit()

        except sqlalchemy.exc.SQLAlchemyError as e:
            db.session.rollback()
            return jsonify(error=f'An error occurred while creating the appointment. {str(e)}'), 500

        finally:
            db.session.close()

        return jsonify(msg='Appointment created successfully.'), 201


# Get appointment by appointment ID
def app_route_get_appointment_by_id(app):

    @app.route('/get-appointment/<int:appointment_id>', methods=['GET'])
    @jwt_required()
    def get_appointment_by_id(appointment_id):
        appointment = db.session.query(Appointment).filter(Appointment.id == appointment_id).first()

        if not appointment:
            return jsonify(msg='Appointment not found.'), 404

        user_role = get_user_role()

        if user_role == 'patient':
            user_id = get_jwt_identity()
            patient_id = get_patient_id(user_id)

            if appointment.patient_id != patient_id:
                return jsonify(error='You do not have permission to view this appointment.'), 403

        elif user_role == 'doctor':
            user_id = get_jwt_identity()
            doctor_id = get_doctor_by_user_id(user_id)

            if appointment.doctor_id != doctor_id:
                return jsonify(error='You do not have permission to view this appointment.'), 403

        elif user_role != 'admin':
            return jsonify(error='You do not have permission to view this appointment.'), 403

        time = appointment.time.strftime('%H:%M:%S')

        return jsonify({
            'id': appointment.id,
            'patientId': appointment.patient_id,
            'patientName': appointment.patient_name,
            'doctorId': appointment.doctor_id,
            'doctorName': appointment.doctor_name,
            'date': appointment.date,
            'time': time,
            'status': appointment.status
        }), 200



# Get all user appointments based on user role
def app_route_get_all_appointments(app):

    @app.route('/get-all-appointments', methods=['GET'])
    @jwt_required()
    def get_all_appointments():
        user_role = get_user_role()

        if user_role == 'patient':
            user_id = get_jwt_identity()
            patient_id = get_patient_id(user_id)
            appointments = db.session.query(Appointment).filter(Appointment.patient_id == patient_id).all()

        elif user_role == 'doctor':
            user_id = get_jwt_identity()
            doctor_id = get_doctor_id(user_id)
            appointments = db.session.query(Appointment).filter(Appointment.doctor_id == doctor_id).all()

        elif user_role == 'admin':
            appointments = db.session.query(Appointment).all()

        else:
            return jsonify(error='You do not have permission to view appointments.'), 403

        if not appointments:
            return jsonify(msg='No appointments found.')

        appointments_list = []
        for appointment in appointments:
            time = appointment.time.strftime('%H:%M:%S')
            appointments_list.append({
                'id': appointment.id,
                'patientId': appointment.patient_id,
                'patientName': appointment.patient_name,
                'doctorId': appointment.doctor_id,
                'doctorName': appointment.doctor_name,
                'date': appointment.date,
                'time': time,
                'status': appointment.status
            })

        return jsonify(appointments_list), 200


# Get doctor's patients from appointments where doctor id is equal to the doctor id of the current user
def app_route_get_doctors_patients(app):

        @app.route('/get-doctors-patients', methods=['GET'])
        @jwt_required()
        def get_doctors_patients():
            user_id = get_jwt_identity()
            doctor_id = get_doctor_id(user_id)
            appointments = db.session.query(Appointment).filter(Appointment.doctor_id == doctor_id).all()


            if not appointments:
                return jsonify(msg='No patients found.')

            patients_list = []
            for appointment in appointments:
                date_of_birth = get_patient_date_of_birth(appointment.patient_id)
                address = get_patient_address(appointment.patient_id)
                phone_number = get_patient_phone_number(appointment.patient_id)
                patients_list.append({
                    'id': appointment.patient_id,
                    'name': appointment.patient_name,
                    'dateOfBirth': date_of_birth,
                    'address': address,
                    'phoneNumber': phone_number
                })

            return jsonify(patients_list), 200


# Delete appointment by appointment ID if user is admin
def app_route_delete_appointment(app):

    @app.route('/delete-appointment/<appointment_id>', methods=['DELETE'])
    @jwt_required()
    def delete_appointment(appointment_id):
        user_role = get_user_role()

        if user_role != 'admin':
            return jsonify(error='You do not have permission to delete appointments.'), 403

        appointment = db.session.query(Appointment).filter(Appointment.id == appointment_id).first()

        if not appointment:
            return jsonify(msg='Appointment not found.'), 404
        try:
            db.session.delete(appointment)
            db.session.commit()

        except sqlalchemy.exc.SQLAlchemyError as e:
            db.session.rollback()
            return jsonify(error=f'An error occurred while deleting the appointment. {str(e)}'), 500

        finally:
            db.session.close()

        return jsonify(msg='Appointment deleted successfully.'), 200


# Set appointment status to approved route using appointment id
def app_route_approve_appointment(app):

    @app.route('/appointment/approve/<int:appointment_id>', methods=['PUT'])
    @jwt_required()
    def approve_appointment(appointment_id):
        user_role = get_user_role()

        if user_role != 'doctor':
            return jsonify(error='You do not have permission to approve appointments.'), 403

        appointment = db.session.query(Appointment).filter(Appointment.id == appointment_id).first()

        if not appointment:
            return jsonify(msg='Appointment not found.'), 404

        appointment.status = 'odobren'

        try:
            db.session.commit()

        except sqlalchemy.exc.SQLAlchemyError as e:
            db.session.rollback()
            return jsonify(error=f'An error occurred while approving the appointment. {str(e)}'), 500

        finally:
            db.session.close()

        return jsonify(msg='Appointment approved successfully.'), 200


# Set appointment status to rejected route using appointment id
def app_route_reject_appointment(app):
    @app.route('/appointment/reject/<int:appointment_id>', methods=['PUT'])
    @jwt_required()
    def reject_appointment(appointment_id):
        user_role = get_user_role()

        if user_role != 'doctor':
            return jsonify(error='You do not have permission to approve appointments.'), 403

        appointment = db.session.query(Appointment).filter(Appointment.id == appointment_id).first()

        if not appointment:
            return jsonify(msg='Appointment not found.'), 404

        appointment.status = 'odbijen'

        try:
            db.session.commit()

        except sqlalchemy.exc.SQLAlchemyError as e:
            db.session.rollback()
            return jsonify(error=f'An error occurred while rejecting the appointment. {str(e)}'), 500

        finally:
            db.session.close()

        return jsonify(msg='Appointment rejected successfully.'), 200


# Set appointment status to canceled route using appointment id
def app_route_cancel_appointment(app):

    @app.route('/appointment/cancel/<int:appointment_id>', methods=['PUT'])
    @jwt_required()
    def cancel_appointment(appointment_id):
        user_role = get_user_role()

        if user_role != 'patient':
            return jsonify(error='You do not have permission to cancel appointments.'), 403

        appointment = db.session.query(Appointment).filter(Appointment.id == appointment_id).first()

        if not appointment:
            return jsonify(msg='Appointment not found.'), 404

        appointment.status = 'otkazan'

        try:
            db.session.commit()

        except sqlalchemy.exc.SQLAlchemyError as e:
            db.session.rollback()
            return jsonify(error=f'An error occurred while canceling the appointment. {str(e)}'), 500

        finally:
            db.session.close()

        return jsonify(msg='Appointment canceled successfully.'), 200
