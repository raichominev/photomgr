# workflow:
# 1. readied images go to local folder for upload
# 2. local service uploads them through proxy service
# 3. ???keywording?/title/category


if __name__ == "__main__":
    driver,db = ini()
    load_reviewed_files(driver,db)