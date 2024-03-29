from enum import Enum
from playsound import playsound
class Keywords(Enum):
    # 검사대상
    product_name = '제품명'
    weight = '중량(수량)'
    barcode = '바코드'
    cert_mark = '인증마크'
    cert_result = '인증정보'

    # 검사 / pass
    inspect = '검사'
    pass_inspect = 'pass'

    # 결과
    accept = '승인'
    error = '오류'
    match_fail = '매칭실패'
    success = '합격'
    fail = '불합격'
    _pass = '유보'

    # 인증마크
    organic = '유기농'
    nonpesticide = '무농약'
    gap = 'GAP(우수관리인증)'
    antibiotic = '무항생제'
    animal = '동물복지'
    haccp = '안전관리인증HACCP'
    pgi = '지리적표시'
    traditional = '전통식품'
    master = '식품명인'
    processed = '가공식품'
    carbon = '저탄소(LOW CARBON)'

    # 검사 헤더
    inspection_opt = '검사대상'
    ocr = '인식결과'
    db = '등록정보'
    score = '싱크율'
    result = '결과'
    final_result = '종합판단'

    # 연속 / 누적 검사 결과
    success_cs = '합격(연속)'
    success_cu = '합격(누적)'
    fail_cs = '불합격(연속)'
    fail_cu = '불합격(누적)'
    pass_cs = '유보(연속)'
    pass_cu = '유보(누적)'
    total = '총계'

    # 알람
    alarm = '알람'

    def kor(self):
        return self.value

    def eng(self):
        return self.name

    def vert_headers(self):
        return [
            self.product_name,
            self.weight,
            self.barcode,
            self.cert_mark,
            self.cert_result
        ]

    def inspection_headers(self):
        return [
            self.inspection_opt,
            self.ocr,
            self.db,
            self.score,
            self.result,
            self.final_result
        ]

    def error_headers(self):
        return [
            self.product_name,
            self.success_cs,
            self.pass_cs,
            self.fail_cs,
            self.success_cu,
            self.pass_cu,
            self.fail_cu,
            self.total
        ]

    def cumul_lst(self):
        return self.error_headers().pop(self.product_name)


class Alarm(Enum):
    warning = 1
    danger = 5
    error = 10
