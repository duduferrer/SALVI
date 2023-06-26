import telebot
import os
import threading
import logging
from db_access import db_search_by_chat_id, db_create_user, db_delete_user, db_upd_time
from user import User
from sheet_access import search_lpna, sync_schedule

#configs
logging.basicConfig(filename='main.log', encoding='utf-8', level=logging.DEBUG)
API_TELEGRAM_TOKEN = os.environ['API_TELEGRAM_TOKEN']
URL_ESCALA = os.environ['URL_ESCALA']
bot = telebot.TeleBot(API_TELEGRAM_TOKEN)
USER = User()

@bot.message_handler(commands=["supervisooor"])
def help(message):
    bot.send_message(message.chat.id,
    '''
    Bot ainda em fase de testes, não esqueça de conferir seu horário.
    Lista de comandos:
     /iniciar - Inicia as configuraçoes do bot
     /sair - Descadastra você dos avisos
     /tempo - Alterar quantos minutos antes você quer ser lembrado
     /supervisooor - Abre o menu de ajuda
     /status - Verifica se você está cadastrado.
     /pernoite - Informações sobre o pernoite
     /horario - Recebe um link para visualizar a escala
     /info - Informações sobre o bot
    '''
    )
@bot.message_handler(commands=["pernoite"])
def night_shift(message):
    logging.info("message /pernoite")
    bot.send_message(message.chat.id,
    '''
    O bot não envia avisos durante o horário do pernoite, de 20:30P de um dia até as 06:30P do outro.
    '''
    )
@bot.message_handler(commands=["horario"])
def schedule(message):
    logging.info("message /horario")
    bot.send_message(message.chat.id,
    f'''
    Veja o horário em: {URL_ESCALA} 
    '''
    )
    
@bot.message_handler(commands=["status"])
def status(message):
    logging.info("message /status")
    if user_already_exists(message):
        res = bot.send_message(message.chat.id,
        '''
        Opa, te encontrei aqui no cadastro! Quando tiver na hora da rendição eu envio uma mensagem.
        '''
        )
        bot.register_next_step_handler(res, upd_time) 
    else:
        bot.send_message(message.chat.id,
        '''
            Não te encontrei no Banco de Dados, envie /iniciar para se cadastrar ou chame o /supervisooor.
        '''
        )   

@bot.message_handler(commands=["info"])
def info(message):
    logging.info("message /info")
    bot.send_message(message.chat.id,
f'''
BOT para telegram desenvolvido por Eduardo Ferrer.
Em caso de dúvidas ou sugestões, https://t.me/ferrereduardo
Código aberto, disponível em https://github.com/duduferrer
''')
    
@bot.message_handler(commands=["tempo"])
def time(message):
    logging.info("message /tempo")
    if user_already_exists(message):
        res = bot.send_message(message.chat.id,
'''
Posso te chamar em 1 ou até 30 minutos antes do turno. O padrão é o tempo de fazer um bolinho, 5 minutos.
Digite o tempo de 1 até 30 minutos.
Exemplo: 5
'''
        )
        bot.register_next_step_handler(res, upd_time) 
    else:
        bot.send_message(message.chat.id,
        '''
            Não te encontrei aqui no Banco de Dados, envie /iniciar para se cadastrar ou chame o /supervisooor.
        '''
        )
def upd_time(message):
    chat_id = message.chat.id
    print(message.text)
    minutes = int(message.text)
    if minutes > 30 or minutes < 1:
        return bot.send_message(chat_id, 
                                '''
                                Não, dollynho! É pra colocar só o número, entre 1 e 30.
                                '''
                                )
    if db_upd_time(str(chat_id), minutes):
        return bot.send_message(chat_id, 
                                f'''
                                Aí, dollynho. Tá feito. Mudei aqui pra te chamar uns {minutes} minutos antes
                                '''
                                )
    else:
        return bot.send_message(chat_id, 
                                '''
                                Aí Dollynho, não consegui mudar o tempo aqui. Tenta de novo. 
                                '''
                                )


@bot.message_handler(commands=["sair"])
def exit(message):
    logging.info("message /sair")
    if user_already_exists(message):
            if db_delete_user(str(message.chat.id)):
                bot.send_message(message.chat.id,
f'''
Feito! Você nao receberá mais avisos. Se precisar de alguma ajuda, chama o /supervisooor. 
'''
                )
            else:
               bot.send_message(message.chat.id,
f'''
Tive um problema para descadastrar você. Tente novamente ou mande uma mensagem para o [suporte](https://t.me/ferrereduardo)
'''
            ) 
    else:
        bot.send_message(message.chat.id,
'''
Não encontrei você no Banco de Dados, envie /iniciar para cadastrar ou chame o /supervisooor.
'''
        )


@bot.message_handler(commands=["iniciar"])
def start(message):
    logging.info("message /iniciar")
    if user_already_exists(message):
            bot.send_message(message.chat.id,
    f'''
        Aí Zé, tu já tá cadastrado. Se precisar de alguma ajuda, chama o /supervisooor. 
    ''')
    else:
        res = bot.send_message(message.chat.id,
'''
Tranquilo, pra começar, me passa o teu indicativo da LPNA.
Exemplo: DOLY
'''
        )
        bot.register_next_step_handler(res, reg_user)
    
def reg_user(message):
    chat_id = str(message.chat.id)
    username = message.chat.username
    lpna = message.text.upper()
    if lpna_is_formatted(lpna):
        name = search_lpna(lpna)
        if name != None:
            user = User(username, chat_id, lpna, name)
            try:
                db_create_user(user)
                return(bot.send_message(chat_id,
f'''
Usuário cadastrado.
Nome: {user.name}.
5 minutos antes da rendição eu te aviso.
'''
                ))
            except:
                logging.error(f"{user.lpna} cannot create on DB")
                return(bot.send_message(chat_id,
f'''
Houve um erro ao realizar o cadastro.
{user.name}, {user.lpna}
'''
                ))
        else:
            logging.error(f"LPNA not found. Tried {user.lpna}")         
            bot.send_message(chat_id,
'''
Não encontrei o seu indicativo. 
Tente de novo. 
/iniciar
'''
            )
    else:
        logging.error(f"LPNA is not correctly formatted. Tried {user.lpna}")
        bot.send_message(chat_id,
f'''
Verifique o formato do indicativo. Use apenas 4 letras.
Tente de novo. 
/iniciar
'''
            )
def lpna_is_formatted(lpna):
    if len(lpna) == 4:
        if lpna.isalpha():
            return True
    else:
        False
                    
        
    
#This function handle all unknown messages, it has to be the last message handling function of the script
@bot.message_handler(func=lambda message: True)
def unscripted_message(message):
    if user_already_exists(message):
        logging.info(f"User already exists, random message")
        bot.send_message(message.chat.id,
f'''
Não saquei o que tu precisa. Se precisar de alguma ajuda, chama o /supervisooor. 
'''     )
    else:
        logging.info(f"Redirect to start, random message")    
        bot.send_message(message.chat.id,
'''
Fala maboy, suave? 
Eu posso te ajudar a não render atrasado.
Digite /iniciar para começar ou chame o /supervisooor para receber ajuda.
'''
        )

def user_already_exists(message):
    chat_id = str(message.chat.id)
    doc = db_search_by_chat_id(chat_id)
    if doc.exists:
        USER.create_from_dict(doc.to_dict())
        logging.info(f"Found user on DB")
        return True    
    else:
        logging.info(f"User not found on DB")
        return False
    
t = threading.Thread(target=sync_schedule)
t.start()  

     
bot.infinity_polling(timeout=10, long_polling_timeout = 5)

    

#TODO IMPLEMENTAR Apos primeira mensagem, buscar user no banco de dados. Se tiver, vai pra outro fluxo.
#TODO IMPLEMENTAR funcoes do help
#TODO IMPLEMENTAR envio de mensagens nos momentos de rendicao, com paramentro variavel de tempo antes.
