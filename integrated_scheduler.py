import time
from datetime import datetime
import os
import asyncio
from croniter import croniter
from loguru import logger
from monitor.btc_ahr999 import fetch_and_push_ahr999_img

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()
LOCAL_DEV = os.getenv('LOCAL_DEV') == 'true'

class CronScheduler:
    """支持 cron 语法的定时任务调度器"""
    
    def __init__(self):
        self.jobs = []
        self.running = False
        
    def add_cron_job(self, cron_expression, job_func, job_name=None, *args, **kwargs):
        """
        添加 cron 定时任务
        
        Args:
            cron_expression (str): cron 表达式，格式：分 时 日 月 周
                                  例如：'0 9 * * *' 表示每天9点执行
                                       '*/5 * * * *' 表示每5分钟执行
                                       '0 9,21 * * *' 表示每天9点和21点执行
            job_func (callable): 要执行的函数
            job_name (str): 任务名称（可选）
            *args, **kwargs: 传递给job_func的参数
        """
        try:
            # 验证 cron 表达式
            cron = croniter(cron_expression, datetime.now())
            next_run = cron.get_next(datetime)
            
            job = {
                'cron_expression': cron_expression,
                'job_func': job_func,
                'job_name': job_name or job_func.__name__,
                'args': args,
                'kwargs': kwargs,
                'next_run': next_run,
                'cron_iter': croniter(cron_expression, datetime.now())
            }
            
            self.jobs.append(job)
            print(f"已添加 cron 任务: {job['job_name']} ({cron_expression})")
            print(f"下次执行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            print(f"添加 cron 任务失败: {e}")
    
    def remove_job(self, job_name):
        """移除指定名称的任务"""
        self.jobs = [job for job in self.jobs if job['job_name'] != job_name]
        print(f"已移除任务: {job_name}")
    
    def list_jobs(self):
        """列出所有任务"""
        if not self.jobs:
            print("当前没有定时任务")
            return
            
        print("\n当前定时任务列表:")
        print("-" * 80)
        for job in self.jobs:
            print(f"任务名称: {job['job_name']}")
            print(f"Cron表达式: {job['cron_expression']}")
            print(f"下次执行: {job['next_run'].strftime('%Y-%m-%d %H:%M:%S')}")
            print("-" * 80)
    
    def run_pending(self):
        """检查并执行到期的任务"""
        now = datetime.now()
        
        for job in self.jobs:
            if now >= job['next_run']:
                try:
                    print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] 执行 cron 任务: {job['job_name']}")
                    
                    # 执行任务
                    if asyncio.iscoroutinefunction(job['job_func']):
                        asyncio.run(job['job_func'](*job['args'], **job['kwargs']))
                    else:
                        job['job_func'](*job['args'], **job['kwargs'])
                    
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 任务 {job['job_name']} 执行完成")
                    
                except Exception as e:
                    error_msg = f"执行 cron 任务 {job['job_name']} 失败: {e}"
                    logger.error(error_msg)
                
                # 修改这里：重新创建croniter对象，使用当前时间作为基准
                job['cron_iter'] = croniter(job['cron_expression'], datetime.now())
                # 计算下次执行时间
                job['next_run'] = job['cron_iter'].get_next(datetime)
                print(f"任务 {job['job_name']} 下次执行时间: {job['next_run'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    def start(self):
        """启动调度器"""
        self.running = True
        print("Cron 调度器已启动")
        
        try:
            while self.running:
                self.run_pending()
                time.sleep(30)  # 每30秒检查一次
        except KeyboardInterrupt:
            print("\nCron 调度器已停止")
        except Exception as e:
            error_msg = f"Cron 调度器运行出错: {e}"
            logger.error(error_msg)
    
    def stop(self):
        """停止调度器"""
        self.running = False

# 创建全局 cron 调度器实例
cron_scheduler = CronScheduler()

# ------------ 任务设置 ------------------

def fetch_and_push_ahr999_card():
    """执行获取并推送ahr999趋势卡片的任务"""
    logger.info(f"执行任务: fetch_and_push_ahr999_card")
    asyncio.run(fetch_and_push_ahr999_img())
# ------------ 任务结束 ------------------

def setup_cron_jobs():
    """设置 cron 定时任务"""
    
    # 使用 cron 语法设置任务
    # 格式：分 时 日 月 周 (0-59 0-23 1-31 1-12 0-7，其中0和7都表示周日)
    
    # 每天早上7:00执行获取并推送ahr999趋势卡片任务
    cron_scheduler.add_cron_job('0 7 * * *', fetch_and_push_ahr999_card, '获取并推送ahr999趋势卡片任务')

    # 每周一、二、三、四、五的7:00执行 日报任务
    # cron_scheduler.add_cron_job('0 7 * * 1,2,3,4,5,6,7', lambda: run_main_task("daily_news"), '日报任务')

def start_cron_scheduler():
    """启动 cron 调度器"""
    setup_cron_jobs()
    cron_scheduler.list_jobs()
    cron_scheduler.start()

if __name__ == "__main__":
    if LOCAL_DEV:
        logger.info("本地开发模式，不启动 cron 调度器")
        # keep_gzh_online_task()
        # run_main_task('daily_news')
    else:
        start_cron_scheduler()     # 使用新的 cron 调度器
