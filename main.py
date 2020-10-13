import json
import re
import time

import cv2
import numpy as np
import requests
from aip import AipOcr
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from baidu_api import APP_ID, API_KEY, SECRET_KEY


def get_driver(browser: str, headless=False, proxy=None):
    if "chrome".startswith(browser.lower()):
        options = webdriver.ChromeOptions()
        options.add_argument('ignore-certificate-errors')
        if headless:
            # options.add_argument("--headless")
            options.headless = True
        if proxy:
            options.add_argument('--proxy-server={0}'.format(proxy.proxy))
        return webdriver.Chrome(options=options)
    elif "firefox".startswith(browser.lower()):
        profile = webdriver.FirefoxProfile()
        profile.accept_untrusted_certs = True
        options = webdriver.FirefoxOptions()
        if headless:
            options.headless = True
        if proxy:
            profile.set_proxy(proxy.selenium_proxy())
        return webdriver.Firefox(firefox_profile=profile, options=options)
    else:
        pass


def convert(src):
    hsv = cv2.cvtColor(src, cv2.COLOR_BGR2HSV)
    low_hsv = np.array([0, 0, 0])
    high_hsv = np.array([180, 255, 46])
    mask = cv2.inRange(hsv, lowerb=low_hsv, upperb=high_hsv)
    mask = 255 - mask  # invert color
    mask = mask[10:28, 20:130]  # crop

    # Reduce noise
    for i in range(1, mask.shape[0] - 1):
        for j in range(1, mask.shape[1] - 1):
            if mask[i, j] == 0 \
                    and mask[i - 1, j] == 255 and mask[i + 1, j] == 255 \
                    and mask[i, j - 1] == 255 and mask[i, j + 1] == 255:
                mask[i, j] = 255

    # cv2.imwrite('file.png', mask)  # debug

    success, encoded_image = cv2.imencode('.png', mask)
    return encoded_image.tobytes()


if __name__ == '__main__':
    ocr_client = AipOcr(APP_ID, API_KEY, SECRET_KEY)

    driver = get_driver(browser="c", headless=True)
    driver.get("https://hdsky.me/")

    with open('cookies.json') as f:
        cookies = f.read()
        cookies = json.loads(cookies)
        for c in cookies:
            driver.add_cookie(c)
    # 刷新页面
    driver.get("https://hdsky.me/")

    logged_in = False
    # 如果没有签到按钮，则认为已经签到
    try:
        driver.find_element_by_id("showup").click()
    except NoSuchElementException as e:
        logged_in = True

    if not logged_in:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "showupimg")))
        captcha_url = driver.find_element_by_id("showupimg").get_attribute("src")

        r = requests.get(captcha_url)
        image = np.asarray(bytearray(r.content))
        image = cv2.imdecode(image, cv2.IMREAD_COLOR)
        png_cv_bytes = convert(image)

        # result = ocr_client.basicAccurate(png_cv_bytes)['words_result'][0]['words']
        result = ocr_client.basicGeneral(png_cv_bytes)['words_result'][0]['words']
        result = re.sub('[\W_]+', '', result)  # 只保留字母和数字
        print(result)  # debug
        if len(result) != 6:  # 验证码只有6位长
            pass

        driver.find_element_by_id("imagestring").send_keys(result)
        time.sleep(0.2)
        driver.find_element_by_id("showupbutton").click()
        time.sleep(0.5)  # TODO 增加延时以等待结果

        # check result
        result = driver.find_element_by_class_name("layui-layer-content").text
        if result == "验证码错误(Wrong CAPTCHA)":
            print(result[:5])
        else:
            match = re.search(r"成功,魔力值加([0-9]+)", result)
            print(match.group(0))
    else:
        print("今日已签到")

    driver.close()
