# def find_name_by_ticker_nyse_nasdaq(name, names, already_in):
#     name = name.strip()
#     filtered_names_objcects = []
#     for x in names:
#         t, n, country, exchange = x
#         filtered_names_objcects.append((n, t, country, exchange))
#     for each_name_object in filtered_names_objcects:
#         if each_name_object[1].lower() == name.lower() and condition_to_write(
#             name, each_name_object[0], already_in
#         ):
#             ticker = name
#             name = clear_name(
#                 slice_names(each_name_object[0]),
#                 lower=False,
#                 spaces=False,
#                 dots=False,
#                 slash_dash=False,
#             )
#             company_info_to_final = [
#                 (
#                     name,
#                     ticker,
#                     each_name_object[2],
#                     True,
#                     each_name_object[3],
#                 )
#             ]
#             return company_info_to_final


# def find_cik_from_objects(name, ticker, file_out=""):
#     name = standartify_str(name, ["-", "/", ",", ".", "&"], to_what=" ")
#     now = deconv_time(datetime.datetime.now())
#     url = "https://efts.sec.gov/LATEST/search-index"
#     params = {
#         "dateRange": "custom",
#         "entityName": name,
#         "startdt": "2001-01-01",
#         "enddt": now,
#     }
#     json_response, condition = get_condition_total_bigger_zero(url, params)
#     if not condition:
#         standartify_str(name, ["'"])
#         params.update(
#             {
#                 "entityName": name,
#             }
#         )
#         json_response, condition = get_condition_total_bigger_zero(url, params)
#     if condition:
#         for each_response_obj in json_response.get("hits").get("hits"):
#             for each_name in each_response_obj.get("_source").get("display_names"):
#                 normalized_name = normalize_name(name)
#                 normalized_each_name = normalize_name(name)
#                 if condition_for_matching_norm_names(
#                     normalized_name, normalized_each_name
#                 ):
#                     cik = re.findall(r"\( cik(\d+)\)", each_name.lower())
#                     if cik:
#                         return cik
#                 if "(" + ticker.lower() in each_name.lower().replace(
#                     " ", ""
#                 ) or ticker.lower() + ")" in each_name.lower().replace(" ", ""):
#                     cik = re.findall(
#                         r"\(cik(\d+)\)", each_name.lower().replace(" ", "")
#                     )
#                     if cik:
#                         return cik[0]
