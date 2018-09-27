from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from src.config import Config
import pymongo


class QuotationCrawler:
    def __init__(self, mongo_uri, mongo_db, mongo_collection):
        self.client = pymongo.MongoClient(mongo_uri)
        self.db = self.client[mongo_db]
        self.collection_name = mongo_collection
        self.driver = webdriver.Chrome()

        self.find_button_path = "//a[contains(@class, 'handler') and contains(@class, 'header-search__handler') and contains(@class, 'header-search__handler-processed')]"
        self.find_input_id = 'edit-search-block-form--2'
        self.article_text_path = ".//div[contains(@class, 'field-name-body')]/div[contains(@class, 'field-items')]//p"
        self.article_source_path = "./div[contains(@class, 'node__content')]/div[contains(@class, 'field-type-taxonomy-term-reference')]//a"
        self.article_tag_path = ".//div[contains(@class, 'node__topics')]//a"
        self.next_page_ref_path = "//div[contains(@class, 'pagination')]//li[contains(@class, 'pager-next')]/a"

    def __del__(self):
        self.client.close()

    def crawl(self, phrases_to_find):
        self.driver.get('https://citaty.info/')
        assert 'Citaty.info' in self.driver.title

        for phrase in phrases_to_find:
            find_button = self.driver.find_element_by_xpath(self.find_button_path)
            find_button.click()

            find_input = self.driver.find_element_by_id(self.find_input_id)
            find_input.clear()
            find_input.send_keys(phrase)
            find_input.send_keys(Keys.RETURN)
            if "Ваш поиск не принес результатов" in self.driver.page_source:
                continue

            elements_per_phrase = 0
            pages_per_phrase = 0

            while True:
                results_element = self.driver.find_element_by_class_name('-results')
                articles = results_element.find_elements_by_tag_name('article')
                for article in articles:
                    text = article.find_element_by_xpath(self.article_text_path).text

                    sources = []
                    source_elements = article.find_elements_by_xpath(self.article_source_path)
                    for source_element in source_elements:
                        sources.append(source_element.text)

                    tags = []
                    tag_elements = article.find_elements_by_xpath(self.article_tag_path)
                    for tag_element in tag_elements:
                        tags.append(tag_element.text)

                    self.db[self.collection_name].insert_one({
                        'text': text,
                        'sources': sources,
                        'tags': tags
                    })
                    elements_per_phrase += 1

                pages_per_phrase += 1

                try:
                    next_page_ref = self.driver.find_element_by_xpath(self.next_page_ref_path)
                    next_page_button = next_page_ref.find_element_by_xpath('..')
                    next_page_button.click()
                except NoSuchElementException:
                    print('NoSuchElementException')
                    break
                except AttributeError:
                    print('AttributeError')
                    break

            print('По запросу "{0}" найдено {1} страниц и собрано {2} записей'.format(phrase, pages_per_phrase, elements_per_phrase))

        self.driver.close()


if __name__ == '__main__':
    crawler = QuotationCrawler(Config.mongo_uri, Config.mongo_db, Config.collection_name)
    crawler.crawl(Config.find_phrases)
