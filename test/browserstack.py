import os
import json
import cStringIO
import sys
import time
import subprocess

from PIL import Image
import selenium.webdriver
import image_comparison


def get_browserstack_webdriver(capabilities):
    capabilities.setdefault('resolution', '1920x1080')
    capabilities.setdefault('browserstack.local', True)
    capabilities.setdefault('browserstack.debug', True)

    config = os.path.expanduser('~/.browserstack.json')
    cfg = json.load(open(config))

    hub = 'http://{user}:{key}@hub.browserstack.com/wd/hub'
    hub = hub.format(**cfg)
    webdriver = selenium.webdriver.Remote(
                command_executor=hub,
                desired_capabilities=capabilities
    )

    webdriver.set_page_load_timeout(60)
    webdriver.implicitly_wait(10)
    return webdriver


class TestRunner(object):
    def __init__(self, driver):
        self.driver = driver

    def __del__(self):
        self.driver.quit()

    def screenshot_element(self, element):
        element = self.driver.find_element_by_id(element)
        location = element.location
        size = element.size

        png = self.driver.get_screenshot_as_png()
        buf = cStringIO.StringIO(png)
        im = Image.open(buf)

        left = location['x']
        top = location['y']
        right = location['x'] + size['width']
        bottom = location['y'] + size['height']

        im = im.crop((left, top, right, bottom))
        return im


def main():
    cap = {
        'os': 'Windows',
        'os_version': '8.1',
        'browser': 'Firefox',
        'browser_version': '30',
    }
    driver = get_browserstack_webdriver(cap)
    driver.get('http://127.0.0.1:8000/test/index.html')

    t = TestRunner(driver)
    time.sleep(1)

    subprocess.call('test/convert_test_images.sh')
    images_bad = []
    images = os.listdir('test/src')
    images.sort()
    for image in images:
        if not image.endswith('.svg'):
            continue
        driver.execute_script('changeTestImage("src/' + image + '");')
        while not driver.execute_script('return checkReady();'):
            time.sleep(1)
        i = t.screenshot_element('output')
        i.save('test/out/' + image + '.png')
        if not image_comparison.compare('test/out/' + image + '.png', 'test/ref/' + image + '.png'):
            images_bad.append(image)

    FAIL = '\033[91m'
    OKGREEN = '\033[92m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

    print '\n' + BOLD + 'Test Results (' + \
            str(len(images) - len(images_bad)) + '/' + str(len(images)) + ' passed)' + \
            ENDC + '\n'
    for image in images:
        output = image
        if image in images_bad:
            output += '\t ' + FAIL + '[FAILED]'
        else:
            output += '\t ' + OKGREEN + '[OK]'
        print output + ENDC

if __name__ == '__main__':
    main()
