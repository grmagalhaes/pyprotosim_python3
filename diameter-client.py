#!/usr/bin/env python
############################################################################
# Copyright (c) 2012, Sergej Srepfler <sergej.srepfler@gmail.com>
# February 2012 -
# Version 0.3, Last change on Oct 30, 2012
# This software is distributed under the terms of BSD license.
#
# Converted to Python 3.7 by Gerson Rodrigues <gerson.rodrigues@n3r.com.br
# July 2019
############################################################################

# Next two lines are to include parent directory for testing
import sys

#sys.path.append("..")
# Remove them normally

# EAP-AKA/AKA' client

from libDiameter import *
import eap
import datetime
import time


def create_CER():
    # Let's build CER
    CER_avps = []
    CER_avps.append(encodeAVP("Origin-Host", ORIGIN_HOST))
    CER_avps.append(encodeAVP("Origin-Realm", ORIGIN_REALM))
    CER_avps.append(encodeAVP("Vendor-Id", dictVENDORid2code('TGPP')))
    CER_avps.append(encodeAVP("Origin-State-Id", ORIGIN_ID))
    CER_avps.append(encodeAVP("Supported-Vendor-Id", dictVENDORid2code('TGPP')))
    CER_avps.append(encodeAVP("Acct-Application-Id", APPLICATION_ID))
    # Create message header (empty)
    CER = HDRItem()
    # Set command code
    CER.cmd = dictCOMMANDname2code("Capabilities-Exchange")
    # Set Hop-by-Hop and End-to-End
    initializeHops(CER)
    # Add AVPs to header and calculate remaining fields
    msg = createReq(CER, CER_avps)
    # msg now contains CER Request as hex string
    return msg


def Payload_Identity():
    # Let's build EAP-Payload Identity AVP
    # Create EAP-Payload (empty)
    EAP = eap.EAPItem()
    # Set command code
    # Remember - Requests normally starts from AAA-> UE, so
    # even when skipped, identity is actually an response
    EAP.cmd = eap.EAP_CODE_RESPONSE
    # Set id
    EAP.id = 1
    # Set type
    EAP.type = eap.EAP_TYPE_IDENTITY
    # Add Identity
    EAP.msg = eap.addEAPIdentity(IDENTITY)
    Payload = eap.encode_EAP(EAP)
    return Payload


def Payload_AKA_Identity(ID, ETYPE):
    # Let's build EAP-Payload with AT_IDENTITY AVP
    # Create EAP-Payload (empty)
    EAP = eap.EAPItem()
    # Set command code
    # Remember - Requests normally starts from AAA-> UE, so
    # even when skipped, identity is actually an response
    EAP.cmd = eap.EAP_CODE_RESPONSE
    # Set id
    EAP.id = ID
    # Set type
    EAP.type = ETYPE
    # Set sub-type
    EAP.stype = eap.dictEAPSUBname2type("AKA-Identity")
    EAP.avps.append(("AT_IDENTITY", IDENTITY))
    Payload = eap.encode_EAP(EAP)
    # Payload now contains EAP-Payload AVP
    return Payload


def Payload_Challenge_Response(ID, RAND, ETYPE):
    # Let's build EAP-Payload Challenge-Response AVP
    # Create EAP-Payload (empty)
    EAP = eap.EAPItem()
    # Set command code
    EAP.cmd = eap.EAP_CODE_RESPONSE
    # Set id
    EAP.id = ID
    # Set type
    EAP.type = ETYPE
    # Set sub-type
    EAP.stype = eap.dictEAPSUBname2type("AKA-Challenge")
    # RAND is copied from Challenge
    # These values can be calculated or entered manually
    # XRES,CK,IK,AK,AKS=eap.aka_calc_milenage(OP,Ki,RAND)
    # Or copy from MAA
    # IK=Identity-Key
    # CK=Confidentiality-Key
    # XRES=SIP-Authorization
    IK = "2d346b8c456223bc7519823a0abc94fd"
    CK = "07fc3189172095ddce5b4ba2bfb70f7f"
    XRES = "e818fbf691ae3b97"
    if EAP.type == eap.EAP_TYPE_AKAPRIME:
        # For AKA'
        KENCR, KAUT, MSK, EMSK, KRE = eap.akap_calc_keys(IDENTITY, CK, IK)
    else:
        # For AKA
        KENCR, KAUT, MSK, EMSK, MK = eap.aka_calc_keys(IDENTITY, CK, IK)
    # Add AT_RES
    EAP.avps.append(("AT_RES", XRES))
    # Add AT_MAC as last
    eap.addMAC(EAP, KENCR, '')
    # Do not add any AVPs after adding MAC
    Payload = eap.encode_EAP(EAP)
    # Payload now contains EAP-Payload AVP
    return Payload


def create_Identity_Request():
    # Let's build Request+Identity-Payload
    REQ_avps = []
    REQ_avps.append(encodeAVP('Session-Id', SESSION_ID))
    REQ_avps.append(encodeAVP("Origin-Host", ORIGIN_HOST))
    REQ_avps.append(encodeAVP("Origin-Realm", ORIGIN_REALM))
    REQ_avps.append(encodeAVP("Destination-Realm", DEST_REALM))
    REQ_avps.append(encodeAVP("Origin-State-Id", ORIGIN_ID))
    REQ_avps.append(encodeAVP('Auth-Application-Id', APPLICATION_ID))
    REQ_avps.append(encodeAVP('Auth-Request-Type', 3))
    Payload = Payload_Identity()
    REQ_avps.append(encodeAVP("EAP-Payload", codecs.decode(Payload, encoding="hex")))
    REQ_avps.append(encodeAVP('Auth-Session-State', 0))
    REQ_avps.append(encodeAVP("User-Name", IDENTITY))
    REQ_avps.append(encodeAVP("Calling-Station-Id", "313171"))
    REQ_avps.append(encodeAVP("RAT-Type", 0))
    REQ_avps.append(encodeAVP("ANID", "HRPD"))
    # Create message header (empty)
    REQ = HDRItem()
    # Set command code
    REQ.cmd = dictCOMMANDname2code("Diameter-EAP")
    # Set Application-Id
    REQ.appId = APPLICATION_ID
    # Set Hop-by-Hop and End-to-End
    initializeHops(REQ)
    # Add AVPs to header and calculate remaining fields
    msg = createReq(REQ, REQ_avps)
    # msg now contains CER Request as hex string
    return msg


def create_Identity_Response(ID, ETYPE):
    # Let's build Response+EAP-Payload with AT_IDENTITY
    REQ_avps = []
    REQ_avps.append(encodeAVP('Session-Id', SESSION_ID))
    REQ_avps.append(encodeAVP("Origin-Host", ORIGIN_HOST))
    REQ_avps.append(encodeAVP("Origin-Realm", ORIGIN_REALM))
    REQ_avps.append(encodeAVP("Destination-Realm", DEST_REALM))
    REQ_avps.append(encodeAVP("Origin-State-Id", ORIGIN_ID))
    REQ_avps.append(encodeAVP('Auth-Application-Id', APPLICATION_ID))
    REQ_avps.append(encodeAVP('Auth-Request-Type', 3))
    Payload = Payload_AKA_Identity(ID, ETYPE)
    REQ_avps.append(encodeAVP("EAP-Payload", Payload.decode("hex")))
    REQ_avps.append(encodeAVP('Auth-Session-State', 0))
    REQ_avps.append(encodeAVP("User-Name", IDENTITY))
    REQ_avps.append(encodeAVP("Calling-Station-Id", "313171"))
    REQ_avps.append(encodeAVP("RAT-Type", 0))
    REQ_avps.append(encodeAVP("ANID", "HRPD"))
    # Create message header (empty)
    REQ = HDRItem()
    # Set command code
    REQ.cmd = dictCOMMANDname2code("Diameter-EAP")
    # Set Application-Id
    REQ.appId = APPLICATION_ID
    # Set Hop-by-Hop and End-to-End
    initializeHops(REQ)
    # Add AVPs to header and calculate remaining fields
    msg = createReq(REQ, REQ_avps)
    # msg now contains CER Request as hex string
    return msg


def create_Challenge_Response(ID, RAND, ETYPE):
    # Let's build Response+Response-Payload
    RES_avps = []
    RES_avps.append(encodeAVP("Session-Id", SESSION_ID))
    RES_avps.append(encodeAVP("Origin-Host", ORIGIN_HOST))
    RES_avps.append(encodeAVP("Origin-Realm", ORIGIN_REALM))
    RES_avps.append(encodeAVP("Destination-Realm", DEST_REALM))
    RES_avps.append(encodeAVP('Auth-Application-Id', APPLICATION_ID))
    RES_avps.append(encodeAVP('Auth-Request-Type', 3))
    Payload = Payload_Challenge_Response(ID, RAND, ETYPE)
    RES_avps.append(encodeAVP("EAP-Payload", codecs.decode(Payload, encoding="hex")))
    RES_avps.append(encodeAVP('Auth-Session-State', 0))
    RES_avps.append(encodeAVP("User-Name", IDENTITY))
    RES_avps.append(encodeAVP("RAT-Type", 0))
    RES_avps.append(encodeAVP("ANID", "HRPD"))
    RES_avps.append(encodeAVP("Service-Selection", "a1"))
    # Create message header (empty)
    RES = HDRItem()
    # Set Proxyable flag
    setFlags(RES, DIAMETER_HDR_PROXIABLE)
    # Set command code
    RES.cmd = dictCOMMANDname2code("Diameter-EAP")
    # Set Application-Id
    RES.appId = APPLICATION_ID
    # Set Hop-by-Hop and End-to-End
    initializeHops(RES)
    # Add AVPs to header and calculate remaining fields
    msg = createReq(RES, RES_avps)
    # msg now contains Response as hex string
    return msg


def create_Disconnect():
    # Let's build Session-Termination
    STR_avps = []
    STR_avps.append(encodeAVP("Session-Id", SESSION_ID))
    STR_avps.append(encodeAVP("Origin-Host", ORIGIN_HOST))
    STR_avps.append(encodeAVP("Origin-Realm", ORIGIN_REALM))
    STR_avps.append(encodeAVP("Destination-Realm", DEST_REALM))
    STR_avps.append(encodeAVP("Origin-State-Id", ORIGIN_ID))
    STR_avps.append(encodeAVP("Auth-Application-Id", APPLICATION_ID))
    STR_avps.append(encodeAVP("User-Name", IDENTITY))
    # DIAMETER_LOGOUT=1
    STR_avps.append(encodeAVP("Termination-Cause", 1))
    # Create message header (empty)
    STR = HDRItem()
    # Set command code
    STR.cmd = dictCOMMANDname2code("Session-Termination")
    # Set Application-Id
    STR.appId = APPLICATION_ID
    # Set Hop-by-Hop and End-to-End
    initializeHops(STR)
    # Add AVPs to header and calculate remaining fields
    msg = createReq(STR, STR_avps)
    # msg now contains Session-Termination Request as hex string
    return msg


def create_Session_Id():
    # The Session-Id MUST be globally and eternally unique
    # <DiameterIdentity>;<high 32 bits>;<low 32 bits>[;<optional value>]
    now = datetime.datetime.now()
    ret = ORIGIN_HOST + ";"
    ret = ret + str(now.year)[2:4] + "%02d" % now.month + "%02d" % now.day
    ret = ret + "%02d" % now.hour + "%02d" % now.minute + ";"
    ret = ret + "%02d" % now.second + str(now.microsecond) + ";"
    ret = ret + IDENTITY[2:16]
    return ret


def dump_Payload(avps):
    for avp in avps:
        (name, value) = decodeAVP(avp)
        if name == 'EAP-Payload':
            print(f'Response: {name}={codecs.decode(value, encoding="hex")})')
            E = eap.decode_EAP(value.encode('hex'))
            for eavp in E.avps:
                (code, data) = eavp
                print(code, '=', data)
        else:
            print(f'Response: {name}=^{value}')


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    LoadDictionary("dictDiameter.xml")
    eap.LoadEAPDictionary("dictEAP.xml")
    HOST = "127.0.0.1"
    PORT = 3870
    ORIGIN_HOST = "localhost"
    ORIGIN_REALM = "localhost"
    now = datetime.datetime.now()
    ORIGIN_ID = str(now.microsecond)
    # 3GPP  SWx=16777265  STa=16777250  S6b=16777272
    APPLICATION_ID = 16777250
    # First digit is 0 for AKA, 6 for AKA'
    IDENTITY = "6121111234561000@127.0.0.1"
    # ETYPE=eap.EAP_TYPE_AKA
    ETYPE = eap.EAP_TYPE_AKAPRIME
    OP = "cdc202d5123e20f62b6d676ac72cb318"
    Ki = "77777777777777777777777777777777"
    # Let's assume that my Diameter messages will fit into 4k
    MSG_SIZE = 4096
    ###########################################################
    # Create unique session ID
    SESSION_ID = create_Session_Id()
    # Connect to server
    Conn = Connect(HOST, PORT)
    ###########################################################
    # Let's build CER
    msg = create_CER()
    # msg now contains CER Request as hex string
    logging.debug("+" * 30)
    # send data
    Conn.send(codecs.decode(msg, encoding="hex"))
    # Receive response
    received = Conn.recv(MSG_SIZE)
    # split header and AVPs
    CEA = HDRItem()
    stripHdr(CEA, codecs.encode(received, encoding="hex"))
    # From CEA we needed Destination-Host and Destination-Realm
    Capabilities_avps = splitMsgAVPs(CEA.msg)
    DEST_HOST = findAVP("Origin-Host", Capabilities_avps)
    DEST_REALM = findAVP("Origin-Realm", Capabilities_avps)
    ###########################################################
    # Create Identity Payload
    msg = create_Identity_Request()
    # msg now contains EAP Request+Identity Payload as hex string
    logging.debug("+" * 30)
    # send data
    Conn.send(codecs.decode(msg, encoding="hex"))
    # Receive response
    received = Conn.recv(MSG_SIZE)
    # Process response
    EAPAnyId = HDRItem()
    stripHdr(EAPAnyId, codecs.encode(received, encoding="hex"))
    Identity_avps = splitMsgAVPs(EAPAnyId.msg)
    Identity_Payload = findAVP("EAP-Payl"
                               "oad", Identity_avps)
    # Display response for better undestanding
    dump_Payload(Identity_avps)
    E = eap.decode_EAP(codecs.encode(Identity_Payload, encoding="hex"))
    ###########################################################
    # If Identity round is not skipped, we need to send AT_IDENTITY
    # Create Identity Payload
    # msg=create_Identity_Response(E.id,ETYPE)
    # msg now contains EAP Request+Identity Payload as hex string
    # logging.debug("+"*30)
    # send data
    # Conn.send(msg.decode("hex"))
    # Receive response
    # received = Conn.recv(MSG_SIZE)
    ###########################################################
    # Process Challenge
    # split header and AVPs
    EAPChallenge = HDRItem()
    stripHdr(EAPChallenge, codecs.encode(received, encoding="hex"))
    # If you do not want to process full msg, you can stop here without any harm
    # We need Payload from EAP-Challenge
    Challenge_avps = splitMsgAVPs(EAPChallenge.msg)
    # Display response for better undestanding
    dump_Payload(Challenge_avps)
    DEST_HOST = findAVP("Origin-Host", Challenge_avps)
    Challenge_Payload = findAVP("EAP-Payload", Challenge_avps)
    logging.debug(f'DEBUG: {codecs.encode(Challenge_Payload, encoding="hex")}')
    RAND = None
    if Challenge_Payload != ERROR:
        # We need AT_RAND to create response
        E = eap.decode_EAP(codecs.encode(Challenge_Payload, encoding="hex"))
        RAND = findAVP("AT_RAND", E.avps)
    ###########################################################
    msg = create_Challenge_Response(E.id, RAND, ETYPE)
    # msg now contains EAP Response as hex string
    logging.debug("+" * 30)
    # send data
    Conn.send(codecs.decode(msg, encoding="hex"))
    # Receive response
    received = Conn.recv(MSG_SIZE)
    # split header and AVPs
    EAPOK = HDRItem()
    stripHdr(EAPOK, codecs.encode(received, encoding="hex"))
    # No decoding is needed.
    # Normally - this is the end.
    ###########################################################
    time.sleep(8)
    # But to clean things up, let's disconnect
    msg = create_Disconnect()
    # msg now contains Disconnect Request as hex string
    logging.debug("-" * 30)
    # send data
    Conn.send(codecs.decode(msg, encoding="hex"))
    # Receive response
    received = Conn.recv(MSG_SIZE)
    # split header and AVPs
    DIS = HDRItem()
    stripHdr(DIS, codecs.encode(received, encoding="hex"))
    # No decoding is needed
    ###########################################################
    # And close the connection
    Conn.close()

######################################################
# History
# 0.2.6 - Apr 27, 2012 - First full-working version
# 0.2.7 - May 25, 2012 - Code cleanup. id matching improoved
# 0.3   - Oct 30, 2012 - lib renamed, eap params fix
# 0.3.1 - Jul 17, 2019 - traslated for Python 3.7
