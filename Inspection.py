from Keywords import Keywords
from enum import Enum


class MarkStatus(Enum):
    success = "success"
    mark_number_error = "mark and producer number doesn\'t match"
    mark_number_check = "mark and producer number should be checked"
    mark_not_found = "mark not found"

    def __str__(self):
        return f"{self.name}"  # self.value


class Inspection():

    def inspect_result(self, result):
        return_dict = {'product_name': [], 'weight': [], 'barcode': [], 'cert_mark': [], 'cert_result': []}

        for key, value in result.items():
            cert_third_num = []
            if key == 'product_name':
                return_dict[key].append(value['name'])
                return_dict[key].append(value['name'])
                if value['status'] == 'success':
                    return_dict[key].append('100%')
                    return_dict[key].append('승인')

            if key == 'weight':
                return_dict[key].append(value['ocr_rslt'])
                return_dict[key].append(value['db'])
                return_dict[key].append(f"{round(value['score'] * 100)}%")
                return_dict[key].append('승인')

            if key == 'barcode':
                return_dict[key].append(value)
                return_dict[key].append(value)
                return_dict[key].append('100%')
                return_dict[key].append('승인')

            if key == 'cert_mark':
                if value:
                    for mark in value:
                        mark_lst = []
                        mark_lst.append(Keywords[mark].kor())
                        cert_numbers = [item['number']['ocr_rslt'] for item in result['cert_result'].values()]
                        mark_lst.append(', '.join([number[2] for number in cert_numbers]))
                        mark_status = [number['mark_status'] for number in result['cert_result'].values()]
                        correct_cnt = 0
                        for status in mark_status:
                            if MarkStatus.success.value == status or MarkStatus.mark_number_check.value == status:
                                correct_cnt += 1
                        raw_score = 0.0

                        if len(mark_status) > 0:
                            raw_score = correct_cnt / len(mark_status)

                        score = f"{round(raw_score * 100)}%"
                        mark_lst.append(score)

                        if correct_cnt == len(mark_status) and raw_score >= 0.9:
                            mark_lst.append('승인')
                        elif MarkStatus.mark_number_error.value in mark_status:
                            mark_lst.append('오류')
                        else:
                            mark_lst.append('매칭실패')
                        return_dict[key].append(mark_lst)
                else:
                    mark_lst = ['', '', '0.0', '매칭실패']
                    return_dict[key].append(mark_lst)

            if key == 'cert_result':
                if value:
                    for num_key, num_value in value.items():
                        cert_lst = []
                        if num_value['in_db']:
                            cert_lst.append(f"{num_value['number']['ocr_rslt']} {num_value['name']['ocr_rslt']}")
                            cert_lst.append(f"{num_value['number']['db']} {num_value['name']['db']}")
                            raw_score = (num_value['name']['score'] + num_value['number']['score']) / 2.0
                            cert_lst.append(f"{round(raw_score * 100)}%")
                            result = '오류'
                            if raw_score >= 0.9:
                                result = '승인'
                            cert_lst.append(result)
                        else:
                            name = ''
                            number = ''
                            if 'name' in num_value and 'number' in num_value:
                                name = num_value['name']['ocr_rslt']
                                number = num_value['number']['ocr_rslt']
                            elif 'number' in num_value.keys():
                                number = num_value['number']['ocr_rslt']
                            elif 'name' in num_value.keys():
                                name = num_value['name']['ocr_rslt']
                            cert_lst.append(f"{name} {number}")
                            cert_lst.append("조회 실패")
                            cert_lst.append('0%')
                            cert_lst.append('매칭실패')
                        return_dict[key].append(cert_lst)
                else:
                    return_dict[key].append(['', '', '0%', '매칭실패'])

        return return_dict
