import re
class validate_nf:
    list_of_codes = []
    list_of_keywords = ["HERSH", "HERSHE", "HERSHEY", "HERSHEYS"]

    def start_validation(self, json):
        results = []
        for item in json["produtos"]:
            sameHash = self.validate_via_hash(item["nome"])
            if sameHash:
                results.append("valid")
                continue
            hasKeyWords = self.validate_via_keywords(item["nome"])
            if hasKeyWords:
                results.append("valid")
                continue
            results.append("invalid")
        return results

    def validate_via_hash(self, item: str):
        for code in self.list_of_codes:
            if hash(item) == code["hash"]:
                print(code["nome"])
                return True
        return False

    def validate_via_keywords(self, item: str):
        separeted_list = [x for x in re.split(r'[\s.,]+', item) if x]
        print(separeted_list)
        for keyword in self.list_of_keywords:
            for word in separeted_list:
                if keyword.upper() in word.upper():
                    print("found Keyword: " + item)
                    return True
        return False
