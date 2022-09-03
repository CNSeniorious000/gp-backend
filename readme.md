[![logo](https://gp.muspimerol.site/favicon.svg)](https://gp.muspimerol.site/)

# 守护青松 Guard Pine

![jwt compatible](http://jwt.io/img/badge-compatible.svg)

## 接口上新计划

- [ ] 亲人信息

  ```json
  [
    {
      "id": "用户标识码",
      "name": "姓名",
      "avatar": "头像url",
      "relation": "选择父亲/母亲/儿子/女儿等",
      "activities": [
        {
          "id": "活动标识码",
          "name": "活动名称",
          "description": "活动详情",
          "situation": "待办/进行中/已完成/已取消"
        }
      ],
      "favorites": [
        {
          "title": "内容标题",
          "abstract": "内容摘要",
          "timeStamp": "时间戳",
          "source": "来源",
          "url": "资源的链接"
        }
      ],
      "notes": []
    }
  ]
  ```

- [ ] 添加提醒
- [ ] 搜索收藏

## **点击此链接可以触发服务器上对该仓库 git pull:** [refresh](https://www.muspimerol.site:9999/refresh)

拉取后将重定向到主页。

如果因为[主站域名](https://muspimerol.site:9999/)
带端口号，不能正常访问，可以访问[CDN加速域名](https://gp.muspimerol.site/)。但这会给我带来额外的费用。

## 用户登录

### 微信直接登录

- id 为 `openid`
- pwd 为 `SK` + `openid`
