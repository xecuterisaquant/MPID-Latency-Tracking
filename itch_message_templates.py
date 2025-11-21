# -*- coding: utf-8 -*-
"""
Message templates for the Nasdaq ITCH data
"""
import struct


def byte_to_str(block):

    # "All alpha fields are ASCII fields which are left justified and padded on the right with spaces."
    block = block.decode('ascii').rstrip()
    return block


def byte_to_int(block):

    block = int.from_bytes(block, byteorder='big')
    return block


def SystemEvent(msgs_blocks):
    """
    Message Type 0 1 “S” System Event Message
    Stock Locate 1 2 Integer Always 0
    Tracking Number 3 2 Integer Nasdaq internal tracking number
    Timestamp 5 6 Integer Nanoseconds since midnight
    Event Code 11 1 Alpha See System Event Codes below
    """

    (locate, track_num, Time, Event) = struct.unpack(
        '>HH6sc', msgs_blocks)
    # locate always zero
    Time = byte_to_int(Time)
    Event = byte_to_str(Event)
    msgs_blocks = {
        'locate': locate,
        'track_num': track_num,
        'Time': Time,
        'Event': Event
    }

    return msgs_blocks


def Stockdirectory(msgs_blocks):
    """
    Message Type 0 1 “R”
    Stock Locate 1 2
    Tracking Number 3 2
    Timestamp 5 6
    Stock 11 8
    Market Category 19 1
    FinancialStatusIndicator 20 1
    Round Lot Size 21 4
    Round Lots Only 25 1
    Issue Classification 26 1
    Issue Sub-•-Type 27 2
    Authenticity 29 1
    Short Sale Threshold Indicator 30 1
    IPO Flag 31 1
    LULDReference Price Tier 32 1
    ETP Flag 33 1
    ETP Leverage Factor 34 4
    Inverse Indicator 38 1
    """

    (locate, track_num, Time, stock, mkt_cat, status, lot_size, lots_only, issue_class,
     issue_sub_typ, authenticity, short_sale, ipo_flag, luld, etp, etp_leverage, inverse) = struct.unpack(
        '>HH6s8sssIcc2scccccIc', msgs_blocks)
    # locate always zero

    Time = byte_to_int(Time)
    stock = byte_to_str(stock)
    mkt_cat = byte_to_str(mkt_cat)
    status = byte_to_str(status)
    lots_only = byte_to_str(lots_only)
    issue_class = byte_to_str(issue_class)
    issue_sub_typ = byte_to_str(issue_sub_typ)
    authenticity = byte_to_str(authenticity)
    short_sale = byte_to_str(short_sale)
    ipo_flag = byte_to_str(ipo_flag)
    luld = byte_to_str(luld)
    etp = byte_to_str(etp)
    inverse = byte_to_str(inverse)

    msgs_blocks = {
        'locate': locate,
        'track_num': track_num,
        'Time': Time,
        'stock': stock,
        'mkt_cat': mkt_cat,
        'status': status,
        'lot_size': lot_size,
        'lots_only': lots_only,
        'issue_class': issue_class,
        'issue_sub_typ': issue_sub_typ,
        'authenticity': authenticity,
        'short_sale': short_sale,
        'ipo_flag': ipo_flag,
        'luld': luld,
        'etp': etp,
        'etp_leverage': etp_leverage,
        'inverse': inverse
    }

    return msgs_blocks


def tradingaction(msgs_blocks):

    (locate, track_num, Time, stock, trd_state, reserved, reason) = struct.unpack(
        '>HH6s8scc4s', msgs_blocks)
    # locate always zero

    Time = byte_to_int(Time)
    stock = byte_to_str(stock)
    trd_state = byte_to_str(trd_state)
    reserved = byte_to_str(reserved)
    reason = byte_to_str(reason)

    msgs_blocks = {
        'locate': locate,
        'track_num': track_num,
        'Time': Time,
        'stock': stock,
        'trd_state': trd_state,
        'reserved': reserved,
        'reason': reason
    }

    return msgs_blocks


def Shortsaletest(msgs_blocks):

    (locate, track_num, Time, stock, Reg_SHO) = struct.unpack(
        '>HH6s8sc', msgs_blocks)
    # locate always zero

    Time = byte_to_int(Time)
    stock = byte_to_str(stock)
    Reg_SHO = byte_to_str(Reg_SHO)

    msgs_blocks = {
        'locate': locate,
        'track_num': track_num,
        'Time': Time,
        'stock': stock,
        'Reg_SHO': Reg_SHO
    }

    return msgs_blocks


def MarketParticipant(msgs_blocks):

    (locate, track_num, Time, mpid, stock, primarymktmaker, mktmakermode,
     mktpartstate) = struct.unpack(
        '>HH6s4s8sccc', msgs_blocks)
    # locate always zero

    Time = byte_to_int(Time)
    stock = byte_to_str(stock)
    mpid = byte_to_str(mpid)
    primarymktmaker = byte_to_str(primarymktmaker)
    mktmakermode = byte_to_str(mktmakermode)
    mktpartstate = byte_to_str(mktpartstate)

    msgs_blocks = {
        'locate': locate,
        'track_num': track_num,
        'Time': Time,
        'mpid': mpid,
        'stock': stock,
        'primarymktmaker': primarymktmaker,
        'mktmakermode': mktmakermode,
        'mktpartstate': mktpartstate
    }

    return msgs_blocks


def MWCBDeclineLevel(msgs_blocks):

    (locate, track_num, Time, level1, level2, level3) = struct.unpack(
        '>HH6sQQQ', msgs_blocks)
    # locate always zero

    Time = byte_to_int(Time)

    msgs_blocks = {
        "locate": locate,
        "track_num": track_num,
        "Time": Time,
        "level1": level1,
        "level2": level2,
        "level3": level3
    }

    return msgs_blocks


def MWCBStatus(msgs_blocks):

    (locate, track_num, Time, breachedlevel) = struct.unpack(
        '>HH6sc', msgs_blocks)
    # locate always zero

    Time = byte_to_int(Time)
    breachedlevel = byte_to_str(breachedlevel)

    msgs_blocks = {
        "locate": locate,
        "track_num": track_num,
        "Time": Time,
        "breachedlevel": breachedlevel
    }

    return msgs_blocks


def QuotingPeriodUpdate(msgs_blocks):

    (locate, track_num, Time, stock, IPOrelase, IPOreleasequalifier, IPOprice) = struct.unpack(
        '>HH6s8sIcI', msgs_blocks)
    # locate always zero

    Time = byte_to_int(Time)
    stock = byte_to_str(stock)
    IPOreleasequalifier = byte_to_str(IPOreleasequalifier)

    msgs_blocks = {
        "locate": locate,
        "track_num": track_num,
        "Time": Time,
        "stock": stock,
        "IPOrelase": IPOrelase,
        "IPOreleasequalifier": IPOreleasequalifier,
        "IPOprice": IPOprice
    }

    return msgs_blocks


def LULDAuctionCollar(msgs_blocks):

    (locate, track_num, Time, stock, refprice, upperprice, lowerprice, extension) = struct.unpack(
        '>HH6s8sIIII', msgs_blocks)
    # locate always zero

    Time = byte_to_int(Time)
    stock = byte_to_str(stock)

    msgs_blocks = {
        "locate": locate,
        "track_num": track_num,
        "Time": Time,
        "stock": stock,
        "refprice": refprice,
        "upperprice": upperprice,
        "lowerprice": lowerprice,
        "extension": extension
    }

    return msgs_blocks


def OperationHalt(msgs_blocks):

    (locate, track_num, Time, stock, mkt_code, halt_action) = struct.unpack(
        '>HH6s8scc', msgs_blocks)
    # locate always zero

    Time = byte_to_int(Time)
    mkt_code = byte_to_str(mkt_code)
    halt_action = byte_to_str(halt_action)
    stock = byte_to_str(stock)

    msgs_blocks = {
        "locate": locate,
        "track_num": track_num,
        "Time": Time,
        "stock": stock,
        "mkt_code": mkt_code,
        "halt_action": halt_action
    }

    return msgs_blocks


def AddOrder(msgs_blocks):

    (locate, track_num, Time, orderid, aggressor, shares, stock, price) = struct.unpack(
        '>HH6sQcI8sI', msgs_blocks)
    # locate always zero

    Time = byte_to_int(Time)
    stock = byte_to_str(stock)
    aggressor = byte_to_str(aggressor)

    msgs_blocks = {
        "locate": locate,
        "track_num": track_num,
        "Time": Time,
        "orderid": orderid,
        "aggressor": aggressor,
        "shares": shares,
        "stock": stock,
        "price": price
    }

    return msgs_blocks


def AddOrderMPID(msgs_blocks):

    (locate, track_num, Time, orderid, aggressor, shares, stock, price, attribute) = struct.unpack(
        '>HH6sQcI8sI4s', msgs_blocks)
    # locate always zero

    Time = byte_to_int(Time)
    stock = byte_to_str(stock)
    aggressor = byte_to_str(aggressor)
    attribute = byte_to_str(attribute)

    msgs_blocks = {
        "locate": locate,
        "track_num": track_num,
        "Time": Time,
        "orderid": orderid,
        "aggressor": aggressor,
        "shares": shares,
        "stock": stock,
        "price": price,
        "attribute": attribute
    }

    return msgs_blocks


def ExecutedMessage(msgs_blocks):

    (locate, track_num, Time, orderid, shares, match_num) = struct.unpack(
        '>HH6sQIQ', msgs_blocks)
    # locate always zero

    Time = byte_to_int(Time)

    msgs_blocks = {
        "locate": locate,
        "track_num": track_num,
        "Time": Time,
        "orderid": orderid,
        "shares": shares,
        "match_num": match_num
    }

    return msgs_blocks


def ExecutedMessagewithPrice(msgs_blocks):

    (locate, track_num, Time, orderid, shares, match_num, printable, price) = struct.unpack(
        '>HH6sQIQcI', msgs_blocks)
    # locate always zero

    Time = byte_to_int(Time)
    printable = byte_to_str(printable)

    msgs_blocks = {
        "locate": locate,
        "track_num": track_num,
        "Time": Time,
        "orderid": orderid,
        "shares": shares,
        "match_num": match_num,
        "printable": printable,
        "price": price
    }

    return msgs_blocks


def OrderCancel(msgs_blocks):

    (locate, track_num, Time, orderid, cancelshares) = struct.unpack(
        '>HH6sQI', msgs_blocks)
    # locate always zero

    Time = byte_to_int(Time)

    msgs_blocks = {
        "locate": locate,
        "track_num": track_num,
        "Time": Time,
        "orderid": orderid,
        "cancelshares": cancelshares
    }

    return msgs_blocks


def OrderDelete(msgs_blocks):

    (locate, track_num, Time, orderid) = struct.unpack('>HH6sQ', msgs_blocks)
    # locate always zero

    Time = byte_to_int(Time)

    msgs_blocks = {
        "locate": locate,
        "track_num": track_num,
        "Time": Time,
        "orderid": orderid
    }

    return msgs_blocks


def OrderReplace(msgs_blocks):

    (locate, track_num, Time, orderid, new_orderid, shares, price) = struct.unpack(
        '>HH6sQQII', msgs_blocks)
    # locate always zero

    Time = byte_to_int(Time)

    msgs_blocks = {
        "locate": locate,
        "track_num": track_num,
        "Time": Time,
        "orderid": orderid,
        "new_orderid": new_orderid,
        "shares": shares,
        "price": price
    }

    return msgs_blocks


def TradeMsgNocross(msgs_blocks):

    (locate, track_num, Time, orderid, aggressor, shares, stock, price, match_num) = struct.unpack(
        '>HH6sQcI8sIQ', msgs_blocks)
    # locate always zero

    Time = byte_to_int(Time)
    aggressor = byte_to_str(aggressor)
    stock = byte_to_str(stock)

    msgs_blocks = {
        "locate": locate,
        "track_num": track_num,
        "Time": Time,
        "orderid": orderid,
        "aggressor": aggressor,
        "shares": shares,
        "stock": stock,
        "price": price,
        "match_num": match_num
    }

    return msgs_blocks


def TradeMsgCross(msgs_blocks):

    (locate, track_num, Time, shares, stock, cross_price, match_num, crosstype) = struct.unpack(
        '>HH6sQ8sIQc', msgs_blocks)
    # locate always zero

    Time = byte_to_int(Time)
    stock = byte_to_str(stock)
    crosstype = byte_to_str(crosstype)

    msgs_blocks = {
        "locate": locate,
        "track_num": track_num,
        "Time": Time,
        "shares": shares,
        "stock": stock,
        "cross_price": cross_price,
        "match_num": match_num,
        "crosstype": crosstype
    }

    return msgs_blocks


def BrokenTrdMsg(msgs_blocks):

    (locate, track_num, Time, match_num) = struct.unpack(
        '>HH6sQ', msgs_blocks)
    # locate always zero

    Time = byte_to_int(Time)

    msgs_blocks = {
        "locate": locate,
        "track_num": track_num,
        "Time": Time,
        "match_num": match_num
    }

    return msgs_blocks


def NetOrdbal(msgs_blocks):

    (locate, track_num, Time, paired_shares, imb_shares, imb_dire,
     stock, farprice, nearprice, currentrefprice, crosstype, pricevariation) = struct.unpack(
        '>HH6sQQc8sIIIcc', msgs_blocks)
    # locate always zero

    Time = byte_to_int(Time)
    stock = byte_to_str(stock)
    imb_dire = byte_to_str(imb_dire)
    crosstype = byte_to_str(crosstype)
    pricevariation = byte_to_str(pricevariation)

    msgs_blocks = {
        "locate": locate,
        "track_num": track_num,
        "Time": Time,
        "paired_shares": paired_shares,
        "imb_shares": imb_shares,
        "imb_dire": imb_dire,
        "stock": stock,
        "farprice": farprice,
        "nearprice": nearprice,
        "currentrefprice": currentrefprice,
        "crosstype": crosstype,
        "pricevariation": pricevariation
    }

    return msgs_blocks


def Retailimprovement(msgs_blocks):

    (locate, track_num, Time, stock, interest) = struct.unpack(
        '>HH6s8sc', msgs_blocks)
    # locate always zero

    Time = byte_to_int(Time)
    stock = byte_to_str(stock)
    interest = byte_to_str(interest)

    msgs_blocks = {
        "locate": locate,
        "track_num": track_num,
        "Time": Time,
        "stock": stock,
        "interest": interest
    }

    return msgs_blocks


def directlisting(msgs_blocks):

    (locate, track_num, Time, stock, openeligibility, minimumallowance,
     maximumallowance, nearexecutionprice, nearexecutiontime, lowerpricerange,
     upperpricerange) = struct.unpack(
        '>HH6s8scIIIQII', msgs_blocks)
    # locate always zero

    Time = byte_to_int(Time)
    stock = byte_to_str(stock)
    openeligibility = byte_to_str(openeligibility)

    msgs_blocks = {
        "locate": locate,
        "track_num": track_num,
        "Time": Time,
        "stock": stock,
        "openeligibility": openeligibility,
        "minimumallowance": minimumallowance,
        "maximumallowance": maximumallowance,
        "nearexecutionprice": nearexecutionprice,
        "nearexecutiontime": nearexecutiontime,
        "lowerpricerange": lowerpricerange,
        "upperpricerange": upperpricerange
    }

    return msgs_blocks
