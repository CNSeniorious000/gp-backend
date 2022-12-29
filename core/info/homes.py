from .common import router, get_html, get_id_reg, sub_str_reg
from pydantic import BaseModel, Field
from fastapi import Path, Query
from enum import Enum
from bs4 import Tag


def parse_resthome_item(li: Tag):
    location, bed_count, price = li.select("ul > li")[:3]
    item = {
        "title": li.div.h4.text.strip(),
        "loc": location.string.lstrip("地址："),
        "bedCount": int(bed_count.string.lstrip("床位数：").rstrip("张")),
        "pricing": price.string.lstrip("收费区间："),
        "resthomeId": int(get_id_reg.findall(li.a["href"])[0])
    }
    if (img_src := li.select_one("img")["src"]) != "/images/no_image.gif":
        item["image"] = img_src
    return item


class Resthome(BaseModel):
    title: str = Field(title="名称")
    loc: str = Field(title="位置")
    bed_count: int = Field(alias="bedCount", title="床位数")
    pricing: str = Field(title="收费区间")
    resthome_id: int = Field(alias="resthomeId", title="机构唯一标识", description="查询详情传这个")
    image: str | None = Field(title="机构图片", description="可能没有，但大部分（尤其是靠前的）都有")


class Region(BaseModel):
    name: str = Field(title="地区名", description="中文名")
    region_id: str = Field(alias="regionId", title="地区唯一标识", description="一般是地区名的拼音，按地域筛选时传这个")


class ResthomesResponse(BaseModel):
    title: str = Field(title="地区名", description="当前搜索的地区")
    count: int = Field(title="结果个数", description="搜索得到的结果个数")
    sub_regions: list[Region] = Field(
        alias="subRegions", title="子区域", description="相关的地域筛选，用户可以从一个地域向下精分"
    )
    results: list[Resthome] = Field(title="结果列表", description="每个机构的预览信息")
    local_hotline: str | None = Field(alias="localHotline", title="当地顾问热线", description="只有少数地区会有这个")

    class Config:
        schema_extra = {"example": {
            "title": "珠海",
            "count": 54,
            "localHotline": "13391635970",
            "subRegions": [{"name": "香洲区", "regionId": "zhxiangzhouqu"}, {"name": "斗门区", "regionId": "doumenqu"}],
            "results": [{
                "title": "湾仔社区养老服务中心",
                "loc": "湾仔街道江海路86号",
                "bedCount": 152,
                "pricing": "3000-6000",
                "resthomeId": 1248029,
                "image": "http://static.yanglao.com.cn/uploads/resthome/1248029/166357615412221602.jpg"
            }, {
                "title": "正方·和园",
                "loc": "翠前南路99号",
                "bedCount": 1200,
                "pricing": "6000-13000",
                "resthomeId": 1247903,
                "image": "http://static.yanglao.com.cn/uploads/resthome/1247903/1662521316668435485.png"
            }, {
                "title": "井岸镇社会福利中心（心益）",
                "loc": "珠海市斗门区井岸镇尖峰前路379号",
                "bedCount": 143,
                "pricing": "1750-6000",
                "resthomeId": 1247754,
                "image": "http://static.yanglao.com.cn/uploads/resthome/1247754/1652077592782914499.jpg"
            }]
        }}


@router.get("/resthomes", response_model=ResthomesResponse)
async def get_resthomes(region: str = None, page: int = 1):
    """rest homes and deeper region information from https://www.yanglao.com.cn/resthome"""

    dom = await get_html(f"/{region or 'resthome'}_{page}")
    data = {
        "title": dom.select_one("div.titbar > h3").string.rstrip("养老院列表"),
        "count": int(get_id_reg.findall(dom.select_one("div.filter span").string)[0]),
        "subRegions": [
            {"name": a.string, "regionId": a["href"].lstrip("/")}
            for a in dom.select("div.filter > dl:nth-child(2) a")
        ],
        "results": [parse_resthome_item(li) for li in dom.select("div.list-view li.rest-item")]
    }

    if tel_anchor := dom.select_one("div.titbar a[href^='tel:']"):
        data["localHotline"] = tel_anchor.string  # ☎ **区养老顾问热线：***

    return data


def reformat_li(tags: list[Tag]):
    return "\n".join(map(lambda li: sub_str_reg.sub("", li.text).replace("\xa0", " "), tags))


class ResthomeDetails(BaseModel):
    title: str = Field(title="机构名")
    loc: str = Field(title="位置")
    bed_count: int = Field(alias="bedCount", title="床位数")
    pricing: str = Field(title="收费区间")
    hits: int = Field(title="访问量", description="网页上叫它“人气”")
    tel: str | None = Field(title="电话号码", description="不一定有，但大部分有")
    general: str = Field(title="基本信息", description="是一个多行字符串，每行都是“key: value”这样的格式")
    contact: str = Field(title="联系方式", description="是一个多行字符串，每行都是“key: value”这样的格式")
    html_intro: str | None = Field(alias="htmlIntro", title="机构介绍", description="是整理过的html字符串")
    html_charge: str = Field(alias="htmlCharge", title="收费标准", description="是整理过的html字符串")
    html_facilities: str = Field(alias="htmlFacilities", title="设施", description="是整理过的html字符串")
    html_service: str = Field(alias="htmlService", title="服务", description="是整理过的html字符串")
    html_notes: str = Field(alias="htmlNotes", title="入住须知", description="是整理过的html字符串")
    images: list[str] = Field(title="图集", description="图片链接的序列")

    class Config:
        schema_extra = {"example": {
            "title": "北京市朝阳区佰康老年公寓（医养结合）",
            "loc": "朝阳区/大兴区/海淀区分布",
            "bedCount": 600,
            "pricing": "2500-6500",
            "hits": "54067",
            "general": """\
所在地区：北京-北京市-朝阳区
机构类型：护理院
机构性质：公建民营
开业时间：2009年
占地面积：11000
建筑面积：8000
床位数：600张
收住对象：半自理/半失能 不能自理/失能卧床 特护 认知障碍 病后康复
收费区间：2500-6500
特色服务：可接收异地老人 具备医保定点资格""",
            "contact": """\
联系人：李院长
地址：朝阳区/大兴区/海淀区分布
网址：https://www.yihebeiyang.com/""",
            "htmlCharge": """\
<div class="cont">
  <strong>
    普惠型医养结合收费：
    护工费（一对三100元/天，每月3000）
    餐费（30元/天，每月900元）
    床位费：医保报销
    特点：在二级医院里面设立养老院
    低保/低收入/困境家庭/残疾人群：最低可以
    本院无任何隐性收费
    老人和家属可放心住本机构
    <span style="background-color:#FFFFFF;">
      详细情况咨询18600990208（同微信）
    </span>
  </strong>
</div>""",
            "htmlFacilities": """\
<div class="cont">
  <a href="http://www.bkyly.cn/" target="_blank">
    <img align="" alt="" height="525" src="http://static.yanglao.com.cn/uploads/resthome/20180708/1531039278108189682.jpg" title="" width="700"/>
  </a>
  <a href="http://www.bkyly.cn/" target="_blank">
    <img align="" alt="" height="525" src="http://static.yanglao.com.cn/uploads/resthome/20180708/1531039289425960248.jpg" title="" width="700"/>
    <br/>
    <img align="" alt="" height="525" src="http://static.yanglao.com.cn/uploads/resthome/20200404/1586005375360443225.jpg" title="" width="700"/>
  </a>
  <br/>
</div>""",
            "htmlService": """\
<div class="cont">
  <span style="font-size:32px;background-color:#FFFFFF;color:#006600;">
    高龄、失能长者 自理、半自理、不自理
    单纯养老院住不了/离不开医疗人群；
    残疾人/低保/低收入
    以上分区管理，分院管理。
  </span>
</div>""",
            "htmlNotes": """\
<div class="cont">
  <div style='color:#333333;background-color:#FFFFFF;padding:0px;margin:0px;font-family:"font-size:15px;'>
    携带老人的身份证和户口本（二者缺一不可）复印件各一张，
    请家属或亲友和老人同时来院，并请携带家属和亲友的身份证等有效证件的原件和复印件一张
  </div>
</div>""",
            "images": [
                "http://static.yanglao.com.cn/uploads/resthome/22606/15254118621845288636.jpg",
                "http://static.yanglao.com.cn/uploads/resthome/22606/15254131751851325629.jpg",
                "http://static.yanglao.com.cn/uploads/resthome/22606/1613812157958172096.jpg",
                "http://static.yanglao.com.cn/uploads/resthome/22606/16142525641539598754.jpg"
            ],
            "tel": "18600990208",
            "htmlIntro": """\
<div class="cont">
 <strong> 北京市朝阳区 </strong> 佰康老年公寓将养老、护理、医疗、相互融合・实现一体化服务。在生活料理、专业护理、及延伸服务等方面，都有非常完备的工作流程和要求。通过指导与帮助，提高长者的生理、心理、认知、社会参与等整体生活能力，同时公寓分区域、专业护理区、自理区、老年康复区、认知症区域。
</div>"""
        }}


@router.get("/resthome/{resthomeId}", response_model=ResthomeDetails)
async def get_resthome_details(resthome_id: int = Path(alias="resthomeId")):
    dom = await get_html(f"/resthome/{resthome_id}.html")
    location, bed_count, price = dom.select("div.inst-summary > ul li")[:3]
    data = {
        "title": dom.select_one("div.inst-summary > h1").string.strip(),
        "loc": location.text.lstrip(location.em.string),
        "bedCount": int(bed_count.text.lstrip(bed_count.em.string).rstrip("张")),
        "pricing": price.text.lstrip(price.em.string),
        "hits": dom.select("div.inst-pic > span")[-1].string.lstrip("人气："),
        "general": reformat_li(dom.select("div.base-info li")),
        "contact": reformat_li(dom.select("div.contact-info li")),
        "htmlCharge": dom.select_one("div.inst-charge > div.cont").prettify(),
        "htmlFacilities": dom.select_one("div.facilities > div.cont").prettify(),
        "htmlService": dom.select_one("div.service-content > div.cont").prettify(),
        "htmlNotes": dom.select_one("div.inst-notes > div.cont").prettify(),
        "images": [img["src"] for img in dom.select("div.inst-photos img")]
    }
    if tel := dom.select_one("#phonenum"):
        data["tel"] = tel.string
    if html_intro := dom.select_one("div.inst-intro > div.cont"):
        data["htmlIntro"] = html_intro.prettify()

    return data


@router.get("/cities", response_model=dict[str, list[Region]])
async def get_cities():
    """sitemap from https://www.yanglao.com.cn/city"""
    return {
        dl.dt.text.strip(): [{"name": a.string, "regionId": a["href"].lstrip("/")} for a in dl.select("dd.list a")]
        for dl in (await get_html("/city")).select("div.citylist > dl")
    }


class ResultType(Enum):
    article = "article"
    resthome = "resthome"


class SearchResultItem(BaseModel):
    title: str = Field(title="网页标题")
    date: str = Field(title="日期", description="yyyy-dd-mm 格式")
    abstract: str = Field(title="摘要", description="百度搜索那样的网页摘要")
    type: ResultType | None = Field(title="结果类型",
                                    description="如果是文章链接则有文章id，如果是机构链接的话则有机构id")
    article_id: int | None = Field(alias="articleId", title="文章id",
                                   description="如果是文章的话有，可以用来进入文章详情页")
    restroom_id: int | None = Field(alias="restroomId", title="机构id",
                                    description="如果是机构的话有，可以用来进入机构详情页")
    href: str = Field(title="搜索结果的原始网页链接",
                      description="搜索的原结果，是一个网页链接，不管是不是文章或者机构都有")
    image: str | None = Field(title="网页图片", description="很少有，而且一般不太清晰")


def parse_search_result(div: Tag):
    result = {
        "title": div.h3.text.strip().rstrip(" - 养老网"),
        "date": div.select_one("span.c-showurl").string.split()[-1],
        "abstract": div.select_one("div.c-abstract").text.strip(),
        "href": (href := div.select_one("a")["href"])
    }
    if img := div.select_one("img"):
        result["image"] = img["src"]
    if "yanglao.com.cn/article/" in href and not href.endswith("/"):
        result["type"] = "article"
        result["articleId"] = int(get_id_reg.findall(href)[0])
    elif "yanglao.com.cn/resthome/" in href and not href.endswith("/"):  # avoid /restroom
        result["type"] = "resthome"
        result["resthomeId"] = int(get_id_reg.findall(href)[0])
    return result


class GlobalSearchResults(BaseModel):
    count: int = Field(title="搜索结果数量")
    results: list[SearchResultItem] = Field(title="搜索结果列表",
                                            description="这个结果是养老网用百度开放的站内搜索平台做的")
    rawUrl: str = Field(title="搜索时用的链接", description="这个没什么用，debug时可能用得上")

    class Config:
        schema_extra = {"example": {
            "count": 2,
            "rawUrl": "http://zhannei.baidu.com/cse/search?s=17154056689837219680&page=0&q=护理",
            "results": [{
                "title": "日常生活护理的注意事项_照料护理",
                "date": "2020-3-3",
                "abstract": "1.理解和尊重老年人,老年人有着丰富的社会经验,为社会贡献了毕生精力,为家庭做了很大贡献,同时,从生活经历而来的自我意识比较强烈。护理工作中应注意理解老年人的特点,不要伤害其尊严。在日常生活照料中,照顾者应注意在语言和行为上尊重...",
                "type": "article",
                "articleId": 514020,
                "restroomId": None,
                "href": "https://www.yanglao.com.cn/article/514020.html",
                "image": None
            }, {
                "title": "居家养老护理服务详细方案(生活护理等十个方面)_照料护理",
                "date": "2022-12-28",
                "abstract": "一、生活护理 1. 服务内容 (1)个人卫生护理 个人卫生包括洗发、梳头、口腔清洁、洗脸、剃胡须、修剪指甲、洗手洗脚、沐浴等护理项目。 (2)生活起居护理 生活起居包括协助进食、协助排泄及如厕、协助移动、更换衣物、卧位护理等护理项目。",
                "type": "article",
                "articleId": 520563,
                "restroomId": None,
                "href": "https://www.yanglao.com.cn/article/520563.html",
                "image": None
            }]
        }}


@router.get("/search", response_model=GlobalSearchResults)
async def global_search(query: str = Query("", title="关键词"), page: int = Query(0, title="分页", ge=0)):
    url = f"http://zhannei.baidu.com/cse/search?s=17154056689837219680&{page=}&q={query}"
    dom = await get_html(url)
    return {
        "count": int(get_id_reg.findall(dom.select_one("span.support-text-top").string)[0]),
        "results": [parse_search_result(div) for div in dom.select("div.result")],
        "rawUrl": url
    }
