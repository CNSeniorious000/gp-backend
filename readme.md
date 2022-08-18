# 守护青松 Guard Pine

## 接口上新计划

- [ ] 子女父母信息
  ```json
  [
    {
      name:string, // 父母昵称
      header:string, // 头像url
      activitv:[ // 父母的活动
        {
          thing:string, // 活动名称
          remark:string, // 活动备注
          isdone:boolean, // 是否完成
        }
        ···
      ],
      favourite:[ // 父母的收藏
        {
          header:string, // 头像url
          name:string, // 昵称
          content:string, // 内容简要
          date:string, // 收藏日期
          from:string, // 收藏的来源
          url:string, // 收藏链接，页面跳转
        }
      ],
      note:[
        {
          // 我真的不懂记录页面是干什么的，比较抽象，庄总问问甲方吧
        }
      ]
    }
  ]
  ```

- [ ] 添加提醒
  ```json
  {
    time:unknow, // 提醒时间，数据类型我也不知道
    thing:string, // 提醒的事件
    remark:string, // 备注
  }
  // 添加的提醒应该就是父母的活动，子女添加提醒之后父母会增加一项活动（？
  ```
- [ ] 搜索收藏
  ```json
  {
    keyword:string // 关键字
  }
  // 返回搜索结果
  ```

## **点击此链接可以触发服务器上对该仓库 git pull:** [refresh](https://www.muspimerol.site:9999/refresh)

拉取后将重定向到主页。

如果因为[主站域名](https://muspimerol.site:9999/)
带端口号，不能正常访问，可以访问[CDN加速域名](https://gp.muspimerol.site/)。但这会给我带来额外的费用。

## 用户登录

### 微信直接登录

- id 为 `openid`
- pwd 为 `SK` + `openid`