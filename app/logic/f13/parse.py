import re

import xmltodict


def regular_ex(reg, text):
    shares = re.findall(reg, text)
    for index, each in enumerate(shares):
        print(index, each)
        shares[index] = int(float(each.replace(",", "")))
    return sum(shares) if shares else None


def txt_parse(new_req, name, share=None):
    name = name.lower()
    print(name)
    new_req = new_req.lower().replace("\n              ", "")
    # wrong=re.findall(rf'{name}.*((?:call|put|bond|option|x\s+x)).*\n',new_req)
    all_reg = [
        rf"{name}.*\s(\d*,*\d*\.*\d+|\d*,\d*,\d*\.*\d+|\d*,\d*,\d*,\d*\.*\d+)\s*(?:sh|\s+s\s+|, ,sh).*\n",
        rf"{name}\D+\n.*\s(\d*,*\d*\.*\d+|\d*,\d*,\d*\.*\d+|\d*,\d*,\d*,\d*\.*\d+|\d+)\s*(?:sh|\s+s\s+).*\n",
        rf"{name}(?:.+\n)+(\d+,*\d*)\nsh\n+defined\n",
        rf'{name}.*\s+"(\d+,*\d*)"\s+sh\s+sole.+\n',
        rf"{name}.*\s(\d+)\s+(?:sole|other)\s+sh\s+\d+\s+sole\n",
        rf"{name}.*\s(\d+)\s+sh\s+\d+\s+sole\s+\d+\s+\d+\n",
        rf"{name}.*,(\d+),sh.*\n",
        rf'{name}.*\s"*(\d*,*\d*\.*\d+|\d*,\d*,\d*\.*\d+|\d*,\d*,\d*,\d*\.*\d+)\s*(?:sh|,sh|shares|full|sole|defined|dfnd|other|oth|stock|define|\ss\s|\.\d+\ssh|.\s+sh).*\n',
    ]
    share = next(
        (regular_ex(reg, new_req) for reg in all_reg if regular_ex(reg, new_req)), None
    )
    print(share)
    return share, "sh"


def xml_parse(new_req, name, share=0):
    delete = re.findall(r">(?:\s*|\n*)<(.*)informationTable", new_req[:1000])
    if len(delete) > 0:
        delete = delete[0]
        if delete and "/" not in delete and len(delete) < 10:
            new_req = new_req.replace(delete, "")
    else:
        delete = re.findall(r"<(.*)informationTable", new_req[:1000])
        if len(delete) > 0:
            delete = delete[0]
            if delete and " " not in delete and "/" not in delete and len(delete) < 10:
                new_req = new_req.replace(delete, "")
    dict_version = {}
    try:
        dict_version = xmltodict.parse(new_req)
    except:
        print(new_req, "KILL_XML")

    if dict_version:
        clas = ""
        try:
            for each_rep in dict_version.get("informationTable").get("infoTable"):
                title_of_class = each_rep.get("titleOfClass").lower().replace(" ", "")
                name_of_issuer = each_rep.get("nameOfIssuer").lower().replace(" ", "")
                name = name.lower().replace(" ", "")
                if (
                    name in title_of_class
                    or name in name_of_issuer
                    or name.replace("/", " ").replace("-", " ") in title_of_class
                    or name.replace("/", " ").replace("-", " ") in name_of_issuer
                    or name.replace("/", "").replace("-", "") in title_of_class
                    or name.replace("/", "").replace("-", "") in name_of_issuer
                ):
                    if each_rep.get("shrsOrPrnAmt").get(
                        "sshPrnamtType"
                    ).lower().replace(" ", "") == "sh" and not each_rep.get("putCall"):
                        print(each_rep.get("shrsOrPrnAmt"))
                        share = share + int(
                            float(each_rep.get("shrsOrPrnAmt").get("sshPrnamt"))
                        )
                        clas = "sh"
        except:
            pass
        return share, clas
