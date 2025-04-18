# 导入必要的库
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from openai import OpenAI
import httpx
import pandas as pd
import json
import re


from django.shortcuts import redirect

def redirect_to_llm(request):
    return redirect('connect_LLM')  # 使用在 urls.py 中定义的 name 参数


# 从Excel文件加载收藏信息
collection_data = pd.read_excel('unit.xlsx')

# ##
# print("test")
# relevant_info_test = collection_data[collection_data['藏品'].str.contains("青花缠枝灵芝纹高足杯的等级是几级？", case=False, na=False)]
# print("test")
# print(relevant_info_test)
# ##

# 确保这个视图只响应GET和POST请求
@require_http_methods(["GET", "POST"])
def connect_LLM(request):
    # 在会话中初始化消息历史，如果不存在，则创建空列表
    if 'message_history' not in request.session:
        request.session['message_history'] = []
    
    # 处理POST请求
    if request.method == "POST":
        # 如果请求中包含清除历史的动作，则清空消息历史
        if 'action' in request.POST and request.POST['action'] == 'clear_history':
            request.session['message_history'] = []
        else:
            # 从POST数据中提取用户的问题，并将其添加到会话的消息历史中
            question = request.POST.get('question', '')
            request.session['message_history'].append({'role': 'user', 'content': question})

            # 根据用户问题，在加载的收藏数据中搜索相关信息
            
            # 定义要处理的字符串
            # 使用正则表达式查找"的"或"位于"或"来自"或"是"或"所属"之前的所有字符
            match = re.search(r'^(.*?)(的|位于|来自|是|所属)', question)

            # 如果找到匹配，输出匹配的部分，否则输出整个字符串
            result = match.group(1) if match else question


            relevant_info = collection_data[collection_data['藏品'].str.contains(result, case=False, na=False)]
            # print(relevant_info)
            # 根据搜索结果构建回答上下文
            context = "Here is what I found about the item: " + str(relevant_info.to_dict()) if not relevant_info.empty else "No specific information found."
            
            ##
            # 如果找到相关信息，将其转换为更易读的字符串格式化输出
            # 确定回答上下文
            if not relevant_info.empty:
                print(relevant_info)  # 打印相关信息以供调试
                info_str = json.dumps(relevant_info.to_dict(orient='records'), indent=4)
                guidance = "Remember that you are a museum Q&A assistant. Please provide a brief Chinese response based on the information I give you, "
                context = f"{guidance}Here is what I found about the item:\n{info_str}"
            else:
                context = "Remember that you are a museum Q&A assistant. Please provide a brief response in Chinese. Could you please provide more specifics?"

            # 配置客户端
            client = OpenAI(
                base_url="https://hk.xty.app/v1",
                api_key="sk-KuS6VKYhcbKqGPfnFfB2D7D8AbF8451f80177b8cC8CbDfAb",  # 请替换成你的OpenAI API密钥
                http_client=httpx.Client(
                    base_url="https://hk.xty.app/v1",
                    follow_redirects=True,
                    timeout=50.0  # 设置请求超时时间
                ),
            )

            # 创建API请求
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": context},
                        {"role": "user", "content": question}
                    ]
                )

                # 提取并处理响应
                if response.choices:
                    answer = response.choices[0].message.content
                else:
                    answer = 'No answer found.'
                request.session['message_history'].append({'role': 'assistant', 'content': answer})
            except httpx.HTTPError as http_err:
                answer = f"An HTTP error occurred: {http_err}"
                request.session['message_history'].append({'role': 'assistant', 'content': answer})
            except Exception as e:
                answer = f"An unexpected error occurred: {str(e)}"
                request.session['message_history'].append({'role': 'assistant', 'content': answer})

            # 标记会话为已修改，以确保改动被保存
            request.session.modified = True

    # 从会话中检索消息历史以显示
    message_history = request.session.get('message_history', [])
    # 返回渲染好的页面，包含消息历史
    return render(request, 'qa_page.html', {'message_history': message_history})
