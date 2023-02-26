import sqlite3
from datetime import date
from nonebot.log import logger


def addUser(userQq: int, userSlug: str) -> int:
    """ add new user
    :param userQq:
    :param userSlug:
    :return: error code
    """
    print(userQq, userSlug)
    db = sqlite3.connect("my.db")
    cur = db.cursor()
    try:
        sql = "insert into userinfo(userQq,userSlug) values (?,?)"
        cur.execute(sql, [userQq, userSlug])
        db.commit()
        db.close()
        return 0
    except sqlite3.Error as e:
        logger.error("添加用户出错。", e)
        db.rollback()
        db.close()
        return -1


def getUserSlugByQq(userQq: int) -> str or int:
    """ get user slug by user qq
    :param userQq:
    :return: user slug or error code
    """
    db = sqlite3.connect("my.db")
    cur = db.cursor()
    try:
        sql = "select userSlug from userinfo where userQq=?"
        cur.execute(sql, [userQq])
        db.commit()
        result = cur.fetchone()
        db.close()
        if result is None:
            return -1
        return result[0]
    except sqlite3.Error as e:
        logger.error(f"获取用户：{userQq}slug出错。", e)
        db.rollback()
        db.close()
        return -1


def getAllUser() -> dict[int:str] or int:
    """ get  all user info in database
    :return: user slug or error code
    """
    db = sqlite3.connect("my.db")
    cur = db.cursor()
    try:
        sql = f"select userQq,userSlug from userinfo"
        cur.execute(sql)
        db.commit()
        results = cur.fetchall()
        cur.close()
        db.close()
        ans = {userQq: userSlug for userQq, userSlug in results}
        return ans
    except:
        db.rollback()
        db.close()
        return -1


def insertAllClockIn(values: dict[int:int], clockin_date: date) -> int:
    """ insert clockin info for all user
    :param values: {userQq:ac_nums}
    :param clockin_date:
    :return: error code
    """
    db = sqlite3.connect("my.db")
    cursor = db.cursor()
    print(values)
    try:
        sql = "insert into user_clockin(userQq,clockin_date,ac_nums)values(?,?,?)"
        params = [(userQq, clockin_date, ac_nums) for userQq, ac_nums in values.items()]
        cursor.executemany(sql, params)
        db.commit()
        db.close()
        return 0
    except sqlite3.Error as e:
        logger.error("插入打卡信息出错。", e)
        db.rollback()
        db.close()
        return -1


def getUserAcNumsByDate(userQq: int, query_date: date) -> int:
    """ inquire about one's ac_nums in a certain date
    :param userQq:
    :param query_date:
    :return: ac_nums or error code
    """
    db = sqlite3.connect("my.db")
    cursor = db.cursor()
    try:
        sql = "select ac_nums from user_clockin where userQq=? and clockin_date=?"
        cursor.execute(sql, [userQq, query_date])
        print(userQq, query_date)
        db.commit()
        result = cursor.fetchone()
        cursor.close()
        db.close()
        if result is not None:
            return result[0]
        return -1
    except sqlite3.Error as e:
        logger.error(f"获取用户：{userQq}打卡数据出错。", e)
        db.rollback()
        db.close()
        return -1


def getAllUserAcNumsByDate(query_date: date) -> dict[int:int] or int:
    """ inquire about everyone's ac_nums in a certain date
    :param query_date:
    :return: {userQq:ac_nums} or error code
    """
    db = sqlite3.connect("my.db")
    cursor = db.cursor()
    try:
        sql = "select userQq,ac_nums from user_clockin where clockin_date=?"
        print(query_date)
        cursor.execute(sql, [query_date])
        db.commit()
        results = cursor.fetchall()
        cursor.close()
        db.close()
        ans = {userQq: ac_nums for userQq, ac_nums in results}
        return ans
    except sqlite3.Error as e:
        logger.error("获取全部用户打卡数据出错。", e)
        db.rollback()
        db.close()
        return -1
