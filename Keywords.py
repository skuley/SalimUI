from enum import Enum
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
    
    # 연속 / 누적 검사 결과
    success_cs = '합격(연속)'
    success_cu = '합격(누적)'
    fail_cs = '불합격(연속)'
    fail_cu = '불합격(누적)'
    pass_cs = '유보(연속)'
    pass_cu = '유보(누적)'
    total = '총'

    def kor(self):
        return self.value

    def eng(self):
        return self.name

    def insp_headers(self):
        return [
            self.product_name,
            self.weight,
            self.barcode,
            self.cert_mark,
            self.cert_result
        ]

    def error_headers(self):
        return [
            self.product_name,
            self.success_cs,
            self.fail_cs,
            self.pass_cs,
            self.success_cu,
            self.fail_cu,
            self.pass_cu,
            self.total
        ]

    def cumul_lst(self):
        return self.error_headers().pop(self.product_name)