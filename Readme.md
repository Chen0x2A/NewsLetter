# 基础功能: 爬取相关文章到本地
1.将config.ini中的weblist下的字段替换为你感兴趣的网站;

2.将keywords下的字段替换为你感兴趣的关键词, 该脚本只会爬取标题带有关键词的文章.

3.运行UpdateNews.py后, 当前路径下会生成relavant_articles.csv和relavant_articles.xlsx文件, 包含目前为止的爬取结果.



note: 注意api用量, 可以先爬取一遍看一下文章数量, 然后再决定是否调用api. 如果要调用api, 重新跑一次UpdateNews.py即可.

# 选项1 - update to notion
1. 确保config.ini中的 `update_to_notion` 参数为yes
2. 获取notion token

进入
https://www.notion.so/my-integrations
, 新建一个名为newsLetter(或者其他名字)的integration, 获取这个integration的notion token, 填写到config.ini下的config.token

3. 将notion页面连接到刚刚建立的integration上.

新建一个notion数据库后, 找到链接中的database_id.
database_id示例: 
https://www.notion.so/<A>?v=<B>
其中?v=之前的内容A是database_id.

将config.ini下的database_id字段;
在数据库右上方, 点击connect to选项, 选择连接到
newsLetter集成
![Alt text](image-1.png)

# 选项2 - 部署到github action, 实现newsLetter功能

1. pull本项目到你自己的仓库
2. 在你的仓库中, 点击Actions,
3. 



# 选项3 - GPT summary
1. 确保config.ini中的`update_to_notion`参数为yes
2. 设置环境变量`OPENAI_API_KEY`为可用的API TOKEN
