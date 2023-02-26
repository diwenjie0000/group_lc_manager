from datetime import timedelta

from nonebot import on_command, require, get_driver
from nonebot.adapters.onebot.v11 import  Event, GroupMessageEvent
from nonebot.adapters.onebot.v11.message import Message
import httpx
import json
from ..service.group_lc_service import *

scheduler = require('nonebot_plugin_apscheduler').scheduler
signup = on_command("绑定", priority=5, block=True)
component_analytics = on_command("查成分", priority=5, block=True)
group_id = 123456
supervise_id = 654321

def At(data: str) -> list[int]:
    """ parse userQq list from '@' info
    :param data:
    :return:
    """
    try:
        data = json.loads(data)
        qq_list = [int(msg["data"]["qq"]) for msg in data["message"] if msg["type"] == "at" and "all" not in str(msg)]
        return qq_list
    except KeyError:
        return []


def getAcNumsByUserSlugFromNet(user_Slug: str) -> int:
    """ get one's current ac_nums
    :param user_Slug:
    :return: ac_nums
    """
    try:
        get_data = httpx.post("https://leetcode.cn/graphql", json={
            "operationName": "userPublicProfile",
            "variables": {
                "userSlug": user_Slug
            },
            "query": "query userPublicProfile($userSlug: String!) {  userProfilePublicProfile(userSlug: $userSlug) {  "
                     "  username    haveFollowed    siteRanking    profile {      userSlug      realName      aboutMe "
                     "     userAvatar      location      gender      websites      skillTags      contestCount      "
                     "asciiCode      medals {        name        year        month        category        __typename  "
                     "    }      ranking {        rating        ranking        currentLocalRanking        "
                     "currentGlobalRanking        currentRating        ratingProgress        totalLocalUsers        "
                     "totalGlobalUsers        __typename      }      skillSet {        langLevels {          langName "
                     "         langVerboseName          level          __typename        }        topics {          "
                     "slug          name          translatedName          __typename        }        topicAreaScores "
                     "{          score          topicArea {            name            slug            __typename     "
                     "     }          __typename        }        __typename      }      socialAccounts {        "
                     "provider        profileUrl        __typename      }      __typename    }    educationRecordList "
                     "{      unverifiedOrganizationName      __typename    }    occupationRecordList {      "
                     "unverifiedOrganizationName      jobTitle      __typename    }    submissionProgress {      "
                     "totalSubmissions      waSubmissions      acSubmissions      reSubmissions      otherSubmissions "
                     "     acTotal      questionTotal      __typename    }    __typename  }} "
        })
        user_public_data = json.loads(get_data.text)
        return int(user_public_data["data"]["userProfilePublicProfile"]["submissionProgress"]["acTotal"])
    except Exception as e:
        logger.error("获取用户公开信息时出错。", e)
        raise e


@signup.handle()
async def _(event: Event):
    message = str(event.get_message()).split()
    userQq = int(event.get_user_id())
    if message[1]:
        userSlug = message[1]
        try:
            getAcNumsByUserSlugFromNet(userSlug)
        except httpx.HTTPError:
            await signup.finish("绑定失败，请输入正确的用户id(leetcode个人主页https://leetcode.cn/u/{userid}/)")
        else:
            temp = getUserSlugByQq(userQq)
            if temp == -1:
                addUser(userQq, userSlug)
            else:
                await signup.finish(f"你已绑定账号{temp}")
        await signup.finish("绑定成功")
    else:
        await signup.finish("绑定失败，请输入正确的用户id(leetcode个人主页https://leetcode.cn/u/{userid}/)")


@component_analytics.handle()
async def _(event: GroupMessageEvent):
    message = str(event.get_message()).split()
    user_list = At(event.json())
    if len(message) > 1:
        m = Message()
        user_set = set(user_list)
        for userQq in user_set:
            userSlug = getUserSlugByQq(userQq)
            print(userSlug)
            if userSlug == -1:
                m += Message("尚未绑定leetcode账户")
                continue
            user_ac_nums = getAcNumsByUserSlugFromNet(userSlug)
            m += Message(f"[CQ:at,qq={userQq}]，")
            m += Message(f"AC总数：{user_ac_nums}")
            last_day = (date.today() + timedelta(-1))
            last_ac_nums = getUserAcNumsByDate(userQq, last_day)
            if last_ac_nums != -1:
                if user_ac_nums >= last_ac_nums:
                    m += Message(f"，今日完成题数：{user_ac_nums - last_ac_nums}。")
                else:
                    m += Message(f"，今日完成题数：{user_ac_nums}。")
            m += Message("\n")
        await component_analytics.finish(m)
    else:
        await component_analytics.finish("打卡宝也不知道哦！")


@scheduler.scheduled_job('cron', hour=12, minute=6, misfire_grace_time=1000)
async def _():
    # 获取用户列表
    driver = get_driver()
    bot_id = str(driver.config.bot_id)
    bot = driver.bots[bot_id]
    group_member_list = await bot.get_group_member_list(group_id=group_id)
    user_id_list = [i['user_id'] for i in group_member_list]

    # 判断未绑定、未打卡、卷王
    not_bind_slug_user_id = []
    not_finish_clockin_user_id = []

    # last_ac_nums {userQq:ac_nums}格式全部用户昨日打卡信息
    # today_ac_nums {userQq:ac_nums}格式全部用户今日打卡信息
    today_ac_nums = {}
    last_day = date.today() + timedelta(days=-1)
    last_ac_nums = getAllUserAcNumsByDate(last_day)

    # userinfo：所有已在数据库内的用户信息
    userinfo = getAllUser()

    for userQq in user_id_list:
        # 发现未绑定用户
        if userQq not in userinfo:
            not_bind_slug_user_id.append(userQq)
            continue
        try:
            userSlug = userinfo[userQq]
            today_ac_nums[userQq] = getAcNumsByUserSlugFromNet(userSlug)
            if userQq not in last_ac_nums:  # 今日绑定的用户不在昨日的打卡信息中
                continue
            if today_ac_nums[userQq] == last_ac_nums[userQq]:
                not_finish_clockin_user_id.append(userQq)
        except:
            print(userQq)
            continue
    insertAllClockIn(today_ac_nums, date.today())
    m1 = Message()
    if len(not_bind_slug_user_id) != 0:
        for i in not_bind_slug_user_id:
            m1 += Message(str(i) + ',')
        m1 += Message("尚未绑定leetcode账号，")

    m2 = Message()
    if len(not_finish_clockin_user_id) != 0:
        for i in not_finish_clockin_user_id:
            m2 += Message(str(i) + ',')
        m2 += Message("今日尚未打卡，")

    m = m1 + m2
    if len(m) == 0:
        m = Message("今日全部打卡")
    await bot.send_private_msg(user_id=supervise_id, message=m)
