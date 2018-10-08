#! /user/bin/evn python
# -*- coding:utf8 -*-

"""

@Author   : Lau James
@Contact  : LauJames2017@whu.edu.cn
@Project  : TKMRC 
@File     : index.py
@Time     : 18-9-30 下午5:54
@Software : PyCharm
@Copyright: "Copyright (c) 2018 Lau James. All Rights Reserved"
"""


from ir.config import Config
from elasticsearch import helpers
import jieba
import logging
import json



class Index(object):
    def __init__(self):
        print("Indexing...")
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')

    @staticmethod
    def data_convert(file_path="../data/DuReaderDemo/search.dev.json"):
        """
        Data convert program for Baidu's DuReader
        :param file_path:
        :return:
        """
        logging.info("convert raw json data into single doc")
        paras = {}
        para_id = 0
        with open(file_path, 'r') as f:
            line = f.readline()
            while line:
                line = json.loads(line.strip(), encoding='utf-8')

                for document in line["documents"]:
                    # question_id = line["question_id"]
                    # question_type = line["question_type"]
                    # segmented_question = ' '.join(token for token in line["segmented_question"])
                    # paras = document["segmented_paragraphs"]
                    for idx, paras_seg in enumerate(document["segmented_paragraphs"]):
                        paragraph = ' '.join(token for token in paras_seg)
                        print('paragraph: ' + paragraph)
                        paras[para_id] = {'paragraph': paragraph}
                        para_id += 1
                line = f.readline()
        logging.info(str(para_id) + ' paragraphs loaded!')
        return paras

    @staticmethod
    def create_index(config):
        """
        Creating index for paragraphs
        :param config:
        :return:
        """
        logging.info("creating '%s' index..." % config.index_name)
        request_body = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "similarity": {
                    "LM": {
                        "type": "LMJelinekMercer",
                        "lambda": 0.4
                    }
                }
            },
            "mappings": {
                config.index_name: {
                    "properties": {
                        "paragraph": {
                            "type": "text",
                            "term_vector": "with_positions_offsets_payloads",
                            # 支持参数yes（term存储），
                            # with_positions（term + 位置）,
                            # with_offsets（term + 偏移量），
                            # with_positions_offsets(term + 位置 + 偏移量)
                            # 对快速高亮fast vector highlighter能提升性能，但开启又会加大索引体积，不适合大数据量用
                            "store": True,
                            "analyzer": "standard",
                            "similarity": "LM"
                        }
                    }
                }
            }
        }
        # 删除先前的索引
        config.es.indices.delete(index=config.index_name, ignore=[400, 404])
        res = config.es.indices.create(index=config.index_name, body=request_body)
        logging.info(res)
        logging.info("Indices are created successfully")

    @staticmethod
    def bulk_index(paras, bulk_size, config):
        """
        Bulk indexing paras
        :param paras:
        :param bulk_size:
        :param config:
        :return:
        """
        logging.info("Bulk index for paragraphs")
        count = 1
        actions = []
        for para_id, para in paras.items():
            action = {
                "_index": config.index_name,
                "_type": config.doc_type,
                "_id": para_id,
                "_source": para
            }

            actions.append(action)
            count += 1

            if len(actions) % bulk_size == 0:
                helpers.bulk(config.es, actions)
                logging.info("bulk index: " + str(count))
                actions = []

        if len(actions) > 0:
            helpers.bulk(config.es, actions)
            logging.info("bulk index: " + str(count))


def main():
    config = Config()
    index = Index()
    paras = index.data_convert(config.doc_path)
    index.create_index(config)
    index.bulk_index(paras=paras, bulk_size=10000, config=config)


if __name__ == '__main__':
    main()