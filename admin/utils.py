import datetime
import logging
from peewee import fn, SQL
from Config import config
from models import V2StatUser, V2User, Db
from datetime import timedelta
from telegram import Update
from telegram.ext import ContextTypes

# 所有字典定义
game_dict = {
    '🎰老虎机': config.TIGER,
    '🎲骰子': config.DICE,
    '🏀篮球': config.BASKETBALL,
    '⚽足球': config.FOOTBALL,
    '🎯飞镖': config.BULLSEYE,
    '🎳保龄球': config.BOWLING,
}

settings_dict = {
    '🏷️标题设置': 'title',
    '📅签到设置': 'checkin',
    '✨抽奖设置': 'lucky',
    #'💬关键词回复': 'keyword_reply',
    #'🆕新成员入群': 'new_members',
}

v2board_dict = {
    '⏱添加时长': 'addtime',
    '⏰减少时长': 'reducetime',
    '🥇昨日排行': 'xx',
    '🏆本月排行': 'xx',
}

def convert_bytes(byte_size):
    """将字节大小转换为人类可读的格式
    
    Args:
        byte_size: 字节大小
        
    Returns:
        格式化后的字符串，如 "1.23 GB"
    """
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
    index = 0
    while byte_size >= 1024 and index < len(suffixes) - 1:
        byte_size /= 1024.0
        index += 1
    return f"{byte_size:.2f} {suffixes[index]}"

def addtime(day: int):
    """为所有有效订阅用户增加订阅时长
    
    Args:
        day: 要增加的天数，正整数
    
    Returns:
        操作结果信息
    """
    if day <= 0:
        logging.warning(f"添加时长失败: 天数必须为正整数，收到值: {day}")
        return "❌ 天数必须为正整数"
        
    try:
        # 确保数据库连接
        try:
            if Db.is_closed():
                logging.info("数据库连接已关闭，正在重新连接...")
                Db.connect()
                logging.info("数据库连接已建立")
        except Exception as conn_error:
            logging.error(f"连接数据库时出错: {str(conn_error)}", exc_info=True)
            return f"❌ 数据库连接失败: {str(conn_error)}"
            
        # 计算增加的秒数
        seconds = day * 24 * 60 * 60
        current_time = int(datetime.datetime.now().timestamp())
        logging.info(f"将为用户增加 {day} 天 ({seconds} 秒)")
        
        # 获取有效用户数量
        try:
            # 修改查询条件，排除已过期的用户
            user_count = V2User.select().where(
                (V2User.expired_at > current_time) & 
                (V2User.expired_at > 0)
            ).count()
            
            if user_count == 0:
                logging.warning("没有找到任何有效订阅用户")
                return "⚠️ 没有找到任何有效订阅用户"
                
            logging.info(f"找到 {user_count} 个有效订阅用户，准备更新时长")
        except Exception as count_error:
            logging.error(f"查询有效用户数量时出错: {str(count_error)}", exc_info=True)
            return f"❌ 查询有效用户时出错: {str(count_error)}"
        
        # 使用事务进行批量更新
        try:
            db = V2User._meta.database
            with db.atomic():
                count = 0
                # 获取所有有效用户列表，避免游标超时
                all_users = list(V2User.select().where(
                    (V2User.expired_at > current_time) & 
                    (V2User.expired_at > 0)
                ))
                total_users = len(all_users)
                logging.info(f"准备处理 {total_users} 个用户")
                
                # 批量更新用户
                batch_size = 100
                for i in range(0, total_users, batch_size):
                    batch = all_users[i:i + batch_size]
                    updates = []
                    for v2_user in batch:
                        try:
                            old_expire = v2_user.expired_at
                            # 确保时间戳有效
                            if not isinstance(old_expire, int) or old_expire <= 0:
                                logging.warning(f"用户 {v2_user.email} 的过期时间无效: {old_expire}")
                                continue
                                
                            new_expire = old_expire + seconds
                            # 防止时间戳溢出
                            if new_expire < 0 or new_expire > 2147483647:  # Unix timestamp max
                                new_expire = 2147483647
                            
                            v2_user.expired_at = new_expire
                            updates.append(v2_user)
                            count += 1
                            logging.info(f"用户 {v2_user.email} 时长从 {old_expire} 更新为 {new_expire}")
                        except Exception as user_error:
                            logging.error(f"处理用户 {v2_user.email} 时出错: {str(user_error)}")
                            continue
                    
                    if updates:
                        V2User.bulk_update(updates, fields=[V2User.expired_at])
                
            if count > 0:
                result = f"✅ 成功为{count}个有效用户增加{day}天的订阅时长"
                logging.info(result)
                return result
            else:
                error_msg = "⚠️ 未能更新任何用户的订阅时长"
                logging.warning(error_msg)
                return error_msg
        except Exception as db_error:
            error_msg = f"数据库操作出错: {str(db_error)}"
            logging.error(error_msg, exc_info=True)
            return f"❌ 数据库操作失败: {str(db_error)}"
    except Exception as e:
        error_type = type(e).__name__
        error_msg = f"增加用户时长出错 [{error_type}]: {str(e)}"
        logging.error(error_msg, exc_info=True)
        return f"❌ 操作失败: {str(e)}"
    finally:
        # 确保数据库连接关闭
        try:
            if not Db.is_closed():
                logging.info("关闭数据库连接")
                Db.close()
        except Exception as close_error:
            logging.error(f"关闭数据库连接时出错: {str(close_error)}", exc_info=True)

async def reducetime(update: Update, context: ContextTypes.DEFAULT_TYPE, days: int):
    """减少时长"""
    try:
        # 确保数据库连接
        if Db.is_closed():
            Db.connect()
            
        # 计算减少的秒数
        seconds = days * 24 * 60 * 60
        current_time = int(datetime.datetime.now().timestamp())
        logging.info(f"将为用户减少 {days} 天 ({seconds} 秒)")
            
        # 获取所有有效订阅用户（不包括不限时用户）
        users = V2User.select().where(
            (V2User.expired_at > current_time) &  # 未过期
            (V2User.expired_at.is_null(False)) &  # 不是不限时用户
            (V2User.expired_at > 0)  # 确保是有效的时间戳
        )
        
        if not users:
            await update.message.reply_text("❌ 没有找到有效的订阅用户")
            return
            
        # 统计处理结果
        success_count = 0
        fail_count = 0
        
        # 使用事务进行批量更新
        db = V2User._meta.database
        with db.atomic():
            # 获取所有有效用户列表，避免游标超时
            all_users = list(users)
            total_users = len(all_users)
            logging.info(f"准备处理 {total_users} 个有效订阅用户")
            
            # 批量更新用户
            batch_size = 100
            for i in range(0, total_users, batch_size):
                batch = all_users[i:i + batch_size]
                updates = []
                for user in batch:
                    try:
                        old_expire = user.expired_at
                        # 确保时间戳有效
                        if not isinstance(old_expire, int) or old_expire <= 0:
                            logging.warning(f"用户 {user.email} 的过期时间无效: {old_expire}")
                            continue
                            
                        # 计算新的到期时间（转换为时间戳）
                        new_expire = old_expire - seconds
                        
                        # 如果新的到期时间小于当前时间，则设置为当前时间
                        if new_expire < current_time:
                            new_expire = current_time
                        
                        user.expired_at = new_expire
                        updates.append(user)
                        success_count += 1
                        logging.info(f"用户 {user.email} 时长从 {old_expire} 更新为 {new_expire}")
                    except Exception as e:
                        logging.error(f"减少用户 {user.email} 时长失败: {str(e)}")
                        fail_count += 1
                
                if updates:
                    V2User.bulk_update(updates, fields=[V2User.expired_at])
                
        # 发送处理结果
        result_message = f"✅ 批量减少时长完成\n"
        result_message += f"成功: {success_count} 个有效用户\n"
        if fail_count > 0:
            result_message += f"失败: {fail_count} 个用户"
        await update.message.reply_text(result_message)
        
    except Exception as e:
        logging.error(f"批量减少时长失败: {str(e)}")
        await update.message.reply_text("❌ 批量减少时长失败，请检查日志")
    finally:
        # 确保数据库连接关闭
        if not Db.is_closed():
            Db.close()

async def addtime(update: Update, context: ContextTypes.DEFAULT_TYPE, days: int):
    """增加时长"""
    try:
        # 确保数据库连接
        if Db.is_closed():
            Db.connect()
            
        # 计算增加的秒数
        seconds = days * 24 * 60 * 60
        current_time = int(datetime.datetime.now().timestamp())
        logging.info(f"将为用户增加 {days} 天 ({seconds} 秒)")
            
        # 获取所有有效订阅用户（不包括不限时用户）
        users = V2User.select().where(
            (V2User.expired_at > current_time) &  # 未过期
            (V2User.expired_at.is_null(False)) &  # 不是不限时用户
            (V2User.expired_at > 0)  # 确保是有效的时间戳
        )
        
        if not users:
            await update.message.reply_text("❌ 没有找到有效的订阅用户")
            return
            
        # 统计处理结果
        success_count = 0
        fail_count = 0
        
        # 使用事务进行批量更新
        db = V2User._meta.database
        with db.atomic():
            # 获取所有有效用户列表，避免游标超时
            all_users = list(users)
            total_users = len(all_users)
            logging.info(f"准备处理 {total_users} 个有效订阅用户")
            
            # 批量更新用户
            batch_size = 100
            for i in range(0, total_users, batch_size):
                batch = all_users[i:i + batch_size]
                updates = []
                for user in batch:
                    try:
                        old_expire = user.expired_at
                        # 确保时间戳有效
                        if not isinstance(old_expire, int) or old_expire <= 0:
                            logging.warning(f"用户 {user.email} 的过期时间无效: {old_expire}")
                            continue
                            
                        # 计算新的到期时间（转换为时间戳）
                        new_expire = old_expire + seconds
                        
                        # 防止时间戳溢出
                        if new_expire < 0 or new_expire > 2147483647:  # Unix timestamp max
                            new_expire = 2147483647
                        
                        user.expired_at = new_expire
                        updates.append(user)
                        success_count += 1
                        logging.info(f"用户 {user.email} 时长从 {old_expire} 更新为 {new_expire}")
                    except Exception as e:
                        logging.error(f"增加用户 {user.email} 时长失败: {str(e)}")
                        fail_count += 1
                
                if updates:
                    V2User.bulk_update(updates, fields=[V2User.expired_at])
                
        # 发送处理结果
        result_message = f"✅ 批量增加时长完成\n"
        result_message += f"成功: {success_count} 个有效用户\n"
        if fail_count > 0:
            result_message += f"失败: {fail_count} 个用户"
        await update.message.reply_text(result_message)
        
    except Exception as e:
        logging.error(f"批量增加时长失败: {str(e)}")
        await update.message.reply_text("❌ 批量增加时长失败，请检查日志")
    finally:
        # 确保数据库连接关闭
        if not Db.is_closed():
            Db.close()

def _get_traffic_stats(start_time: int, end_time: int, title: str) -> str:
    """获取指定时间范围内的流量统计
    
    Args:
        start_time: 开始时间戳
        end_time: 结束时间戳
        title: 标题
        
    Returns:
        格式化的流量统计信息
    """
    medal_list = ["🥇", "🥈", "🥉"]  # 前三名使用奖牌
    number_list = ["4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]  # 其他名次使用数字
    
    try:
        # 确保数据库连接
        if Db.is_closed():
            Db.connect()
            
        # 记录时间范围
        logging.info(f"查询时间范围: {datetime.datetime.fromtimestamp(start_time)} 到 {datetime.datetime.fromtimestamp(end_time)}")
            
        # 首先获取所有用户的ID和邮箱映射
        users = V2User.select(V2User.id, V2User.email)
        users_count = users.count()
        users_map = {user.id: user.email for user in users}
        user_ids = list(users_map.keys())  # 转换为列表
        logging.info(f"找到 {users_count} 个用户")
        
        if not users_map:
            logging.warning("未找到任何用户")
            return f"{title}\n————————————\n暂无用户数据"

        # 检查是否有流量记录
        record_count = V2StatUser.select().where(
            (V2StatUser.record_at >= start_time) &
            (V2StatUser.record_at <= end_time)
        ).count()
        logging.info(f"时间范围内共有 {record_count} 条流量记录")

        # 查询流量数据
        traffic_query = (V2StatUser
                     .select(
                         V2StatUser.user_id,
                         fn.SUM(V2StatUser.u).alias('up'),
                         fn.SUM(V2StatUser.d).alias('down'),
                         fn.SUM(V2StatUser.u + V2StatUser.d).alias('total')
                     )
                     .where(
                         (V2StatUser.record_at >= start_time) &
                         (V2StatUser.record_at <= end_time) &
                         (V2StatUser.user_id << user_ids)  # 使用 << 操作符代替 in_
                     )
                     .group_by(V2StatUser.user_id)
                     .having(fn.SUM(V2StatUser.u + V2StatUser.d) > 0)  # 只显示有流量的用户
                     .order_by(fn.SUM(V2StatUser.u + V2StatUser.d).desc())
                     .limit(10))
        
        logging.info(f"执行查询SQL: {traffic_query.sql()}")
        
        traffic_data = list(traffic_query)
        logging.info(f"查询到 {len(traffic_data)} 个用户的流量数据")
        
        results_list = []
        for data in traffic_data:
            if data.user_id in users_map:
                results_list.append({
                    'email': users_map[data.user_id],
                    'up': data.up or 0,
                    'down': data.down or 0,
                    'total': data.total or 0
                })
                logging.info(f"用户 {users_map[data.user_id]} 的流量数据: ↑{data.up or 0}, ↓{data.down or 0}, 总计{data.total or 0}")
        
        if not results_list:
            logging.warning("未找到任何有效的流量记录")
            return f"{title}\n————————————\n暂无流量记录"

        text = f"{title}\n————————————\n"
        
        # 计算总流量以显示百分比
        total_traffic = sum(result['total'] for result in results_list)
        logging.info(f"总流量: {total_traffic}")
        
        for idx, result in enumerate(results_list):
            try:
                percentage = (result['total'] / total_traffic * 100) if total_traffic > 0 else 0
                
                # 使用奖牌或数字表情
                if idx < len(medal_list):
                    rank_emoji = medal_list[idx]
                else:
                    rank_emoji = number_list[idx - len(medal_list)]
                
                # 添加进度条
                progress = "▓" * int(percentage / 10) + "░" * (10 - int(percentage / 10))
                
                text += f"{rank_emoji} {result['email']}\n"
                text += f"├─ ⬆️ {convert_bytes(result['up'])}\n"
                text += f"├─ ⬇️ {convert_bytes(result['down'])}\n"
                text += f"├─ 📊 {convert_bytes(result['total'])}\n"
                text += f"└─ {progress} {percentage:.1f}%\n\n"
                
                logging.info(f"用户 {result['email']} - 上传: {convert_bytes(result['up'])}, "
                           f"下载: {convert_bytes(result['down'])}, 总计: {convert_bytes(result['total'])}")
            except Exception as e:
                logging.error(f"处理用户数据时出错: {str(e)}", exc_info=True)
                continue

        # 添加总计信息
        text += f"📈 总流量: {convert_bytes(total_traffic)}"
        return text
        
    except Exception as e:
        error_msg = f"获取流量统计出错: {str(e)}"
        logging.error(error_msg, exc_info=True)
        return f"❌ 获取流量统计失败: {str(e)}"
    finally:
        try:
            if not Db.is_closed():
                Db.close()
        except Exception as close_error:
            logging.error(f"关闭数据库连接时出错: {str(close_error)}", exc_info=True)

def statDay():
    """获取昨日用户流量排行榜"""
    try:
        # 确保数据库连接
        try:
            if Db.is_closed():
                logging.info("数据库连接已关闭，正在重新连接...")
                Db.connect()
                logging.info("数据库连接已建立")
        except Exception as conn_error:
            logging.error(f"连接数据库时出错: {str(conn_error)}", exc_info=True)
            return f"❌ 数据库连接失败: {str(conn_error)}"
            
        # 计算昨天的时间范围
        now = datetime.datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        start_time = int(yesterday_start.timestamp())
        end_time = int(today_start.timestamp())
        
        logging.info(f"昨日统计时间范围: 从 {datetime.datetime.fromtimestamp(start_time)} 到 {datetime.datetime.fromtimestamp(end_time)}")
        
        return _get_traffic_stats(start_time, end_time, "📊 昨日流量排行榜")
        
    except Exception as e:
        error_msg = f"获取流量排行出错: {str(e)}"
        logging.error(error_msg, exc_info=True)
        return f"❌ 获取流量数据出错: {str(e)}"
    finally:
        # 确保数据库连接关闭
        try:
            if not Db.is_closed():
                logging.info("关闭数据库连接")
                Db.close()
        except Exception as close_error:
            logging.error(f"关闭数据库连接时出错: {str(close_error)}", exc_info=True)

def statMonth():
    """获取本月用户流量排行榜"""
    try:
        # 确保数据库连接
        try:
            if Db.is_closed():
                logging.info("数据库连接已关闭，正在重新连接...")
                Db.connect()
                logging.info("数据库连接已建立")
        except Exception as conn_error:
            logging.error(f"连接数据库时出错: {str(conn_error)}", exc_info=True)
            return f"❌ 数据库连接失败: {str(conn_error)}"
            
        # 计算本月的时间范围
        now = datetime.datetime.now()
        # 本月第一天的开始时间
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # 下个月第一天的开始时间
        if now.month == 12:
            next_month = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            next_month = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
            
        start_time = int(month_start.timestamp())
        end_time = int(next_month.timestamp())
        
        logging.info(f"本月统计时间范围: 从 {datetime.datetime.fromtimestamp(start_time)} 到 {datetime.datetime.fromtimestamp(end_time)}")
        
        return _get_traffic_stats(start_time, end_time, "📊 本月流量排行榜")
        
    except Exception as e:
        error_msg = f"获取流量排行出错: {str(e)}"
        logging.error(error_msg, exc_info=True)
        return f"❌ 获取流量数据出错: {str(e)}"
    finally:
        # 确保数据库连接关闭
        try:
            if not Db.is_closed():
                logging.info("关闭数据库连接")
                Db.close()
        except Exception as close_error:
            logging.error(f"关闭数据库连接时出错: {str(close_error)}", exc_info=True)
